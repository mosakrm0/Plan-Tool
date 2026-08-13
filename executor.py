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
    
    for step in job.steps:
        reporter.log(job.name, f"> Step: {step.name}", Colors.BLUE)
        
        # Use the absolute docker_path we just resolved
        docker_cmd = [
            docker_path, "run", "--rm",
            "-v", f"{target_dir}:/workspace",
            "-w", "/workspace",
            job.image,
            "sh", "-c", step.run
        ]
        
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
                reporter.log(job.name, f"❌ Step '{step.name}' failed (exit {process.returncode})", Colors.RED)
                reporter.set_status(job.name, Status.FAILED, total_duration)
                return False, total_duration

        except Exception as e:
            # Catch any other unexpected OS errors cleanly
            total_duration = time.time() - job_start_time
            reporter.log(job.name, f"❌ Failed to execute process: {e}", Colors.RED)
            reporter.set_status(job.name, Status.FAILED, total_duration)
            return False, total_duration

    total_duration = time.time() - job_start_time
    reporter.log(job.name, f"✅ Job completed successfully", Colors.GREEN)
    reporter.set_status(job.name, Status.PASSED, total_duration)
    
    return True, total_duration