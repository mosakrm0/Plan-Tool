import threading
import json
from enum import Enum

class Status(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class Colors:
    RESET = "\033[0m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"

class Reporter:
    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()

    def init_job(self, job_name: str):
        self.results[job_name] = {"status": Status.PENDING, "duration": 0.0}

    def set_status(self, job_name: str, status: Status, duration: float = 0.0):
        with self.lock:
            if job_name not in self.results:
                self.results[job_name] = {}
            self.results[job_name]["status"] = status
            self.results[job_name]["duration"] = duration

    def log(self, job_name: str, message: str, color: str = Colors.RESET):
        clean_message = message.rstrip('\n')
        if not clean_message:
            return
            
        with self.lock:
            for line in clean_message.split('\n'):
                print(f"{color}[{job_name}]{Colors.RESET} {line}")

    def print_summary(self):
        print("\n" + "="*45)
        print("🏁 PIPELINE SUMMARY")
        print("="*45)
        
        for job_name, data in self.results.items():
            status = data["status"]
            duration = data["duration"]
            
            color = Colors.RESET
            if status == Status.PASSED: color = Colors.GREEN
            elif status == Status.FAILED: color = Colors.RED
            elif status == Status.SKIPPED: color = Colors.YELLOW
            elif status == Status.RUNNING: color = Colors.BLUE
            
            print(f"{color}{job_name.ljust(20)} | {status.value.ljust(8)} | {duration:.2f}s{Colors.RESET}")
        
        print("="*45 + "\n")

    # --- NEW: JSON REPORTING METHODS ---
    def get_report_dict(self) -> dict:
        """Converts the internal results into a standard dictionary."""
        report = {}
        for job_name, data in self.results.items():
            report[job_name] = {
                "status": data["status"].value,
                "duration": round(data["duration"], 2)
            }
        return {"jobs": report}
        
    def save_json_report(self, filepath: str = "report.json"):
        """Saves the pipeline results to a file."""
        with open(filepath, 'w') as f:
            json.dump(self.get_report_dict(), f, indent=2)
        print(f"📄 Saved JSON report to {filepath}")