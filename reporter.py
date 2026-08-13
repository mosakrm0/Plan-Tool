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

    # --- JSON REPORTING METHODS WITH SECRET MASKING ---
    def _mask_secrets_in_obj(self, obj, secret_values):
        """Recursively replace any occurrences of secret values in strings with '***'."""
        if not secret_values:
            return obj
        if isinstance(obj, dict):
            return {k: self._mask_secrets_in_obj(v, secret_values) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._mask_secrets_in_obj(v, secret_values) for v in obj]
        if isinstance(obj, str):
            masked = obj
            for s in secret_values:
                if s and s in masked:
                    masked = masked.replace(s, '***')
            return masked
        return obj

    def get_report_dict(self, secret_values: list = None) -> dict:
        """Converts the internal results into a standard dictionary and masks secrets if provided."""
        report = {}
        for job_name, data in self.results.items():
            report[job_name] = {
                "status": data["status"].value,
                "duration": round(data["duration"], 2)
            }
        out = {"jobs": report}
        return self._mask_secrets_in_obj(out, secret_values or [])
        
    def save_json_report(self, filepath: str = "report.json", secret_values: list = None):
        """Saves the pipeline results to a file, masking any provided secrets."""
        with open(filepath, 'w') as f:
            json.dump(self.get_report_dict(secret_values=secret_values), f, indent=2)
        print(f"📄 Saved JSON report to {filepath}")
