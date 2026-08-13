import subprocess
import time
import os
import shutil
from typing import Tuple
from parser import Job
from reporter import Reporter, Status, Colors

def execute_job(job: Job, reporter: Reporter, cwd: str = None) -> Tuple[bool, float]:
    reporter.set_status(job.name, Status.RUNNING)
    reporter.log(job.name, f"--- Starting Job in {job.image} ---", Colors.BLUE)
    
    job_start_time = time.time()
    
    target_dir = os.path.abspath(cwd or os.getcwd())
    
    # --- NEW: Safely check for Docker before running ---
    docker_path = shutil.which("docker")
    if not docker_path:
        reporter.log(job.name, "❌ Error: 'docker' command not found. Is Docker Desktop installed and running?", Colors.RED)
        reporter.set_status(job.name, Status.FAILED, 0.0)
        return False, 0.0
    # ---------------------------------------------------
    
    # Combine all steps into a single container run so that side-effects (e.g., pip installs) persist between steps
    # Build a shell command that echoes step headers and executes each step; stop on first failure
    step_cmds = []
    for step in job.steps:
        # Escape single quotes in the command and step name to avoid breaking the shell string
        safe_run = step.run.replace("'", "'\"'\"'")
        safe_name = step.name.replace("'", "'\"'\"'")
        step_cmds.append(f"echo '--- STEP: {safe_name}'; {safe_run}")

    combined_shell = "set -e; " + " && ".join(step_cmds)

    docker_cmd = [
        docker_path, "run", "--rm",
    ]

    # Mount workspace
    docker_cmd += ["-v", f"{target_dir}:/workspace", "-w", "/workspace"]

    # Pass environment variables into the container
    for k, v in (job.env or {}).items():
        docker_cmd += ["-e", f"{k}={v}"]

    # If job requests docker service/dind or uses docker image, and host socket exists, mount it (fallback)
    host_sock = '/var/run/docker.sock'
    if any('docker' in s for s in (job.services or [])) or ('docker' in (job.image or '').lower()):
        if os.path.exists(host_sock):
            reporter.log(job.name, f"⚠️ Using host Docker socket fallback: mounting {host_sock}", Colors.YELLOW)
            docker_cmd += ["-v", f"{host_sock}:{host_sock}", "-e", f"DOCKER_HOST=unix://{host_sock}"]
        else:
            reporter.log(job.name, "⚠️ Docker service requested but host socket not available; service may fail.", Colors.YELLOW)

    # Run container as the current host user when possible so files created inside the workspace are owned correctly
    try:
        uid = os.getuid()
        gid = os.getgid()
        docker_cmd += ["-u", f"{uid}:{gid}"]
    except AttributeError:
        # os.getuid/getgid not available on Windows; skip
        pass

    # Finally the image + command
    docker_cmd += [job.image, "sh", "-c", combined_shell]

    try:
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if process.stdout:
            for line in process.stdout:
                reporter.log(job.name, line, Colors.GRAY)

        process.wait()

        if process.returncode != 0:
            total_duration = time.time() - job_start_time
            reporter.log(job.name, f"❌ Job failed (exit {process.returncode})", Colors.RED)
            reporter.set_status(job.name, Status.FAILED, total_duration)
            return False, total_duration

    except Exception as e:
        total_duration = time.time() - job_start_time
        reporter.log(job.name, f"❌ Failed to execute process: {e}", Colors.RED)
        reporter.set_status(job.name, Status.FAILED, total_duration)
        return False, total_duration

    total_duration = time.time() - job_start_time
    reporter.log(job.name, f"✅ Job completed successfully", Colors.GREEN)
    reporter.set_status(job.name, Status.PASSED, total_duration)

    return True, total_duration