import sys
import os
import subprocess
import tempfile
import concurrent.futures
import argparse
import urllib.request
import urllib.error
import json
import sysconfig
from typing import Optional, Dict
import yaml
from parser import load_pipeline, PipelineError
from graph import get_execution_order
from executor import execute_job
from reporter import Reporter, Status, Colors


def load_kv_file(path: str) -> Dict[str,str]:
    """Load variables/secrets from a simple .env or YAML file.

    - .env style: KEY=VALUE lines
    - YAML: top-level mapping
    """
    out = {}
    if not path or not os.path.exists(path):
        return out
    try:
        if path.lower().endswith(('.yml', '.yaml')):
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        out[str(k)] = '' if v is None else str(v)
        else:
            # treat as .env
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    out[k.strip()] = v.strip()
    except Exception:
        print(f"⚠️ Failed to read vars/secrets file: {path}")
    return out


def merge_vars_into_jobs(pipeline, extra_vars: Dict[str,str], secrets: Dict[str,str]):
    """Merge pipeline-level vars, job-level env and provided extra vars/secrets into job.env.

    Precedence: pipeline file vars < CLI extra_vars < job-level env < secrets
    """
    extra_vars = extra_vars or {}
    secrets = secrets or {}

    if hasattr(pipeline, 'variables'):
        pipeline.variables.update({k: str(v) for k, v in extra_vars.items()})
    else:
        pipeline.variables = {k: str(v) for k, v in extra_vars.items()}

    for job in pipeline.jobs.values():
        base_env = dict(pipeline.variables or {})
        job_env = getattr(job, 'env', {}) or {}
        merged = {**base_env, **job_env}
        merged.update({k: str(v) for k, v in secrets.items()})
        job.env = merged

__version__ = "0.0.1"
UPDATE_URL = "https://raw.githubusercontent.com/mosakrm0/Plan-Tool/main/version.txt"

def check_for_updates():
    """Silently checks a remote URL for a newer version."""
    try:
        req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            latest_version = response.read().decode('utf-8').strip()
            
            if latest_version and latest_version != __version__:
                print(f"{Colors.YELLOW}🌟 Update available! You are running v{__version__}, but v{latest_version} is out.{Colors.RESET}")
                print(f"{Colors.GRAY}Run the install script again to update.{Colors.RESET}\n")
    except Exception:
        pass


def perform_update():
    """Run the platform-appropriate installer to update Plan.

    - On Unix-like systems this runs the remote install.sh via curl | bash
    - On Windows it runs the remote install.ps1 via Invoke-WebRequest | Invoke-Expression

    This function shells out and requires network access and any privileges the installers need.
    """
    print("🔄 Checking and applying update...")
    try:
        if os.name == 'nt':
            # PowerShell command to run remote install.ps1
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Invoke-WebRequest -UseBasicParsing -Uri https://raw.githubusercontent.com/mosakrm0/plan-tool/main/install.ps1 | Invoke-Expression"
            ]
        else:
            # curl | bash approach for Unix-like
            cmd = ["/bin/bash", "-c", "curl -fsSL https://raw.githubusercontent.com/mosakrm0/plan-tool/main/install.sh | bash"]

        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            print(f"✅ Update applied. You may need to restart your shell to pick up changes.")
            return True
        else:
            print(f"⚠️ Update failed (exit {proc.returncode}).")
            return False
    except FileNotFoundError:
        print("⚠️ Installer tool not found on this system (bash/powershell). Update aborted.")
        return False
    except Exception as e:
        print(f"⚠️ Update failed: {e}")
        return False

def fix_windows_path():
    """Automatically adds the Python Scripts folder to the Windows User PATH."""
    if os.name != 'nt':
        print("❌ This command is only needed on Windows.")
        sys.exit(1)
        
    import winreg
    user_scripts_dir = sysconfig.get_path("scripts", f"{os.name}_user")
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        current_path, _ = winreg.QueryValueEx(key, "Path")
        
        if user_scripts_dir in current_path:
            print(f"✅ Your PATH is already configured correctly!\n({user_scripts_dir} is present)")
        else:
            new_path = current_path + ";" + user_scripts_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"✅ Successfully added to PATH:\n{user_scripts_dir}")
            print(f"⚠️  IMPORTANT: You MUST close this terminal and open a new one for the changes to take effect.")
            
        winreg.CloseKey(key)
        
    except Exception as e:
        print(f"❌ Failed to update registry: {e}")
        print(f"Please manually add {user_scripts_dir} to your System PATH.")
    sys.exit(0)

def send_webhook(url: str, payload: dict):
    print(f"\n🌐 Sending webhook to {url}...")
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ Webhook delivered (Status: {response.getcode()})")
    except urllib.error.URLError as e:
        print(f"⚠️ Failed to send webhook: {e}")

def run_job_task(job_name: str, pipeline, reporter: Reporter, cwd: str = None) -> bool:
    job = pipeline.jobs[job_name]
    
    should_skip = False
    with reporter.lock:
        for needed_job in job.needs:
            if reporter.results[needed_job]["status"] in (Status.FAILED, Status.SKIPPED):
                should_skip = True
                break
                
    if should_skip:
        reporter.log(job_name, "⚠️ Skipped due to failed dependency.", Colors.YELLOW)
        reporter.set_status(job_name, Status.SKIPPED)
        return False

    success, _ = execute_job(job, reporter, cwd=cwd)
    return success

def run_pipeline(filepath: str, cwd: str = None, webhook_url: str = None, extra_vars: Optional[Dict[str,str]] = None, secrets: Optional[Dict[str,str]] = None, report_output_dir: Optional[str] = None):
    try:
        pipeline = load_pipeline(filepath)
        get_execution_order(pipeline)
    except PipelineError as e:
        print(f"❌ Pipeline error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

    # Merge extra variables and secrets into the pipeline and jobs
    merge_vars_into_jobs(pipeline, extra_vars or {}, secrets or {})

    reporter = Reporter()
    for job_name in pipeline.jobs:
        reporter.init_job(job_name)

    in_degree = {job: 0 for job in pipeline.jobs}
    unlocks = {job: [] for job in pipeline.jobs}
    
    for job_name, job in pipeline.jobs.items():
        for needed_job in job.needs:
            unlocks[needed_job].append(job_name)
            in_degree[job_name] += 1

    pipeline_success = True
    # Print a summary line showing how many variables/secrets were applied (values redacted)
    var_count = len(pipeline.variables) if hasattr(pipeline, 'variables') else 0
    secret_count = len(secrets)
    print(f"⚡ Starting pipeline execution in [{pipeline.image}]... (vars={var_count}, secrets=***hidden***)\n")

    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures_to_job = {}
        
        for job_name in pipeline.jobs:
            if in_degree[job_name] == 0:
                futures_to_job[pool.submit(run_job_task, job_name, pipeline, reporter, cwd)] = job_name

        while futures_to_job:
            done, _ = concurrent.futures.wait(futures_to_job, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                finished_job = futures_to_job.pop(future)
                success = future.result()
                if not success:
                    pipeline_success = False
                    
                for dependent in unlocks[finished_job]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        futures_to_job[pool.submit(run_job_task, dependent, pipeline, reporter, cwd)] = dependent

    reporter.print_summary()
    # Save JSON report with secrets masked. Use explicit report_output_dir when provided so temporary clones
    # don't cause the report to disappear after exit.
    out_dir = report_output_dir or (cwd or ".")
    out_path = os.path.join(out_dir, "report.json")
    reporter.save_json_report(out_path, secret_values=list(secrets.values()) if secrets else None)
    
    if webhook_url:
        payload = reporter.get_report_dict(secret_values=list(secrets.values()) if secrets else None)
        send_webhook(webhook_url, payload)
        
    if not pipeline_success:
        sys.exit(1)

def find_pipeline_file(target_dir: str, specified_file: str = None) -> str:
    """Finds the pipeline file, supporting many CI filename conventions (GitHub Actions, GitLab, Plan, etc.).

    Priority order:
      1. explicit specified_file
      2. well-known top-level names (.mini-ci.yml, .plan.yml, .gitlab-ci.yml, .ci.yml)
      3. GitHub Actions workflows (.github/workflows/*.yml)
      4. fallback: search for any YAML containing a 'jobs:' or top-level 'script:' indicators
    """
    if specified_file:
        path = os.path.join(target_dir, specified_file)
        if not os.path.exists(path):
            print(f"❌ Could not find specified pipeline: {specified_file} in {target_dir}")
            sys.exit(1)
        return path

    # 1) Check common top-level filenames (collect candidates rather than returning immediately)
    common_names = [
        ".mini-ci.yml", ".mini-ci.yaml", ".plan.yml", ".plan.yaml",
        ".ci.yml", ".ci.yaml", "gitlab-ci.yml", "gitlab-ci.yaml", ".gitlab-ci.yml", ".gitlab-ci.yaml"
    ]
    candidates = []
    for name in common_names:
        path = os.path.join(target_dir, name)
        if os.path.exists(path):
            candidates.append(path)

    # 2) GitHub Actions workflows
    gh_workflows_dir = os.path.join(target_dir, '.github', 'workflows')
    if os.path.isdir(gh_workflows_dir):
        for fname in sorted(os.listdir(gh_workflows_dir)):
            if fname.endswith(('.yml', '.yaml')):
                candidates.append(os.path.join(gh_workflows_dir, fname))

    # 3) Walk the tree for obvious CI files (gitlab, circleci, any .yml that looks like a pipeline)
    for root, dirs, files in os.walk(target_dir):
        # skip common virtual env/build folders to avoid noise
        skip_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', 'dist', 'build'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for fname in files:
            lf = fname.lower()
            if lf in ("gitlab-ci.yml", "gitlab-ci.yaml", "circleci/config.yml"):
                candidates.append(os.path.join(root, fname))
                continue

            if lf.endswith(('.yml', '.yaml')):
                # Heuristic: peek into the file looking for 'jobs:' or 'script:' to identify CI files
                try:
                    with open(os.path.join(root, fname), 'r', encoding='utf-8') as f:
                        head = f.read(16 * 1024)
                        if 'jobs:' in head or '\nscript:' in head or '\nstages:' in head:
                            candidates.append(os.path.join(root, fname))
                except Exception:
                    continue

    # Remove duplicates while preserving order
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)

    if not uniq:
        print(f"❌ Could not find a pipeline YAML file in {target_dir}")
        sys.exit(1)

    if len(uniq) == 1:
        return uniq[0]

    # Prefer top-level well-known names if present
    for name in common_names:
        candidate_path = os.path.join(target_dir, name)
        if candidate_path in uniq:
            print(f"⚠️ Multiple pipeline-like files found. Choosing {candidate_path} (pass --pipeline to select explicitly).")
            return candidate_path

    # Prefer a file inside .github/workflows next
    for c in uniq:
        if os.path.normpath('.github' + os.sep + 'workflows') in os.path.normpath(c):
            print(f"⚠️ Multiple pipeline-like files found. Choosing {c} from .github/workflows (pass --pipeline to select explicitly).")
            return c

    # Fallback: print list and return the first
    print("⚠️ Multiple pipeline-like YAML files detected; listing candidates (choose with --pipeline):")
    for c in uniq:
        print(' -', c)
    print(f"⚠️ Selecting first candidate: {uniq[0]}")
    return uniq[0]

def run_from_repo(repo_url: str, pipeline_filename: str = None, webhook_url: str = None, extra_vars: Optional[Dict[str,str]] = None, secrets: Optional[Dict[str,str]] = None):
    # Save report to caller's current working directory so temporary clone removal doesn't delete it
    report_output_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📦 Cloning {repo_url}...")
        clone_proc = subprocess.run(
            ["git", "clone", repo_url, "."], 
            cwd=temp_dir, 
            capture_output=True, 
            text=True
        )
        
        if clone_proc.returncode != 0:
            print(f"❌ Failed to clone repository:\n{clone_proc.stderr}")
            sys.exit(1)
            
        print("✅ Clone successful!")
        
        pipeline_path = find_pipeline_file(temp_dir, pipeline_filename)
        print(f"🔍 Found pipeline at {pipeline_path}")
        run_pipeline(pipeline_path, cwd=temp_dir, webhook_url=webhook_url, extra_vars=extra_vars, secrets=secrets, report_output_dir=report_output_dir)

def main():
    check_for_updates()
    
    parser = argparse.ArgumentParser(
        description=f"plan (v{__version__}): A lightweight, parallel CI/CD runner.",
        epilog=(
            "Examples:\n"
            "  plan --repo https://github.com/user/repo.git\n"
            "  plan --local ./my-project -v image=mosakram/flaskapp -v tag=0.2 -s DOCKER_PASS=secret\n"
            "  plan --repo https://gitlab.com/user/repo.git --pipeline .gitlab-ci.yml -v image=custom/image\n"
            "Notes:\n  Use -v/--var to set pipeline variables and -s/--secret to inject secrets (secrets are not printed)."
        )
    )
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--repo', type=str, help="URL of the Git repository to clone and run.")
    group.add_argument('--local', type=str, help="Path to a local directory to run in (does not clone).")
    group.add_argument('--fix-path', action='store_true', help="Automatically fixes the 'command not found' Windows error.")
    
    parser.add_argument('--pipeline', type=str, default=None, help="Name of the pipeline file.")
    parser.add_argument('--webhook', type=str, help="Optional URL to POST the JSON report to.")
    parser.add_argument('--var', '-v', action='append', help="Set pipeline variable KEY=VALUE (can repeat)")
    parser.add_argument('--secret', '-s', action='append', help="Set secret KEY=VALUE (can repeat). Secrets are not printed.")
    parser.add_argument('--vars-file', type=str, help="Path to a .env or YAML file with variables (KEY=VALUE or YAML mapping)")
    parser.add_argument('--secrets-file', type=str, help="Path to a .env or YAML file with secrets")

    parser.add_argument('--update', action='store_true', help='Check for and install the latest release (platform installer)')

    args = parser.parse_args()

    # If user explicitly asked to update, run installer and exit
    if getattr(args, 'update', False):
        success = perform_update()
        sys.exit(0 if success else 1)

    # Helper to parse KEY=VALUE lists
    def parse_kv_list(kv_list):
        out = {}
        if not kv_list:
            return out
        for entry in kv_list:
            if '=' not in entry:
                print(f"⚠️ Ignoring malformed variable/secret: {entry}. Expected KEY=VALUE")
                continue
            k, v = entry.split('=', 1)
            out[k] = v
        return out

    extra_vars = parse_kv_list(args.var)
    secrets = parse_kv_list(args.secret)

    # Load vars/secrets files (if provided) and merge. CLI flags override file contents.
    file_vars = load_kv_file(args.vars_file) if getattr(args, 'vars_file', None) else {}
    file_secrets = load_kv_file(args.secrets_file) if getattr(args, 'secrets_file', None) else {}
    merged_vars = {**file_vars, **extra_vars}
    merged_secrets = {**file_secrets, **secrets}
    extra_vars = merged_vars
    secrets = merged_secrets

    if args.fix_path:
        fix_windows_path()
    elif args.repo:
        run_from_repo(args.repo, args.pipeline, args.webhook, extra_vars=extra_vars, secrets=secrets)
    elif args.local:
        local_dir = os.path.abspath(args.local)
        pipeline_path = find_pipeline_file(local_dir, args.pipeline)
        print(f"🔍 Found pipeline at {pipeline_path}")
        # Save report to the directory where the user invoked the command, not the project dir
        report_output_dir = os.getcwd()
        run_pipeline(pipeline_path, cwd=local_dir, webhook_url=args.webhook, extra_vars=extra_vars, secrets=secrets, report_output_dir=report_output_dir)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()