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
from parser import load_pipeline, PipelineError
from graph import get_execution_order
from executor import execute_job
from reporter import Reporter, Status, Colors

# --- NEW: Version Tracking ---
__version__ = "1.0.0"

UPDATE_URL = "https://raw.githubusercontent.com/mosakrm0/Plan-Tool/main/version.txt"

def check_for_updates():
    """Silently checks a remote URL for a newer version."""
    try:
        req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        # Use a short timeout so we don't slow down the CLI if the internet is down
        with urllib.request.urlopen(req, timeout=1.5) as response:
            latest_version = response.read().decode('utf-8').strip()
            
            if latest_version and latest_version != __version__:
                print(f"{Colors.YELLOW}🌟 Update available! You are running v{__version__}, but v{latest_version} is out.{Colors.RESET}")
                print(f"{Colors.GRAY}Run 'git pull' and 'pip install -e .' to update.{Colors.RESET}\n")
    except Exception:
        # If offline or repo isn't public yet, just fail silently
        pass

# --- NEW: Auto-Path Fixer for Windows ---
def fix_windows_path():
    """Automatically adds the Python Scripts folder to the Windows User PATH."""
    if os.name != 'nt':
        print("❌ This command is only needed on Windows.")
        sys.exit(1)
        
    import winreg
    import sysconfig
    
    # Get the EXACT user-level scripts directory for this specific Python version
    user_scripts_dir = sysconfig.get_path("scripts", f"{os.name}_user")
    
    try:
        # Open the Windows Registry for the current user's environment
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        current_path, _ = winreg.QueryValueEx(key, "Path")
        
        # Check if the exact user scripts directory is in the PATH
        if user_scripts_dir in current_path:
            print(f"✅ Your PATH is already configured correctly!\n({user_scripts_dir} is present)")
        else:
            # Append the scripts directory to the path
            new_path = current_path + ";" + user_scripts_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"✅ Successfully added to PATH:\n{user_scripts_dir}")
            print(f"⚠️  IMPORTANT: You MUST close this terminal and open a new one for the changes to take effect.")
            
        winreg.CloseKey(key)
        
    except Exception as e:
        print(f"❌ Failed to update registry: {e}")
        print(f"Please manually add {user_scripts_dir} to your System PATH.")
    sys.exit(0)

# ... [Keep your existing run_job_task, run_pipeline, send_webhook, find_pipeline_file, and run_from_repo functions exactly the same] ...

def main():
    # Check for updates immediately when the CLI is invoked
    check_for_updates()
    
    parser = argparse.ArgumentParser(
        description=f"plan (v{__version__}): A lightweight, parallel CI/CD runner.",
        epilog="Example: plan --repo https://github.com/user/repo.git"
    )
    
    # We make the main group NOT required so we can run --fix-path on its own
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--repo', type=str, help="URL of the Git repository to clone and run.")
    group.add_argument('--local', type=str, help="Path to a local directory to run in (does not clone).")
    group.add_argument('--fix-path', action='store_true', help="Automatically fixes the 'command not found' Windows error.")
    
    parser.add_argument('--pipeline', type=str, default=None, help="Name of the pipeline file.")
    parser.add_argument('--webhook', type=str, help="Optional URL to POST the JSON report to.")

    args = parser.parse_args()

    # Route the request
    if args.fix_path:
        fix_windows_path()
    elif args.repo:
        run_from_repo(args.repo, args.pipeline, args.webhook)
    elif args.local:
        local_dir = os.path.abspath(args.local)
        pipeline_path = find_pipeline_file(local_dir, args.pipeline)
        print(f"🔍 Found pipeline at {pipeline_path}")
        run_pipeline(pipeline_path, cwd=local_dir, webhook_url=args.webhook)
    else:
        # If they didn't pass --local, --repo, or --fix-path, show the help menu
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()