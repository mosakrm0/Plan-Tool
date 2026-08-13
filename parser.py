import yaml
from dataclasses import dataclass, field
from typing import List, Dict

class PipelineError(Exception):
    pass

@dataclass
class Step:
    name: str
    run: str

@dataclass
class Job:
    name: str
    steps: List[Step]
    needs: List[str] = field(default_factory=list)
    image: str = "ubuntu:latest"

@dataclass
class Pipeline:
    jobs: Dict[str, Job]
    image: str = "ubuntu:latest"  # NEW: Global image track

def load_pipeline(filepath: str) -> Pipeline:
    try:
        with open(filepath, 'r') as file:
            raw_data = yaml.safe_load(file)
    except FileNotFoundError:
        raise PipelineError(f"Could not find pipeline file: {filepath}")
    except yaml.YAMLError as e:
        raise PipelineError(f"Invalid YAML syntax: {e}")

    if not raw_data or 'jobs' not in raw_data:
        raise PipelineError("Pipeline must contain a 'jobs' key at the root level.")

    # --- NEW: Extract the global image ---
    global_image = raw_data.get('image', 'ubuntu:latest')

    parsed_jobs = {}
    for job_name, job_data in raw_data['jobs'].items():
        if 'steps' not in job_data or not job_data['steps']:
            raise PipelineError(f"Job '{job_name}' must contain at least one step.")

        parsed_steps = []
        for step_data in job_data['steps']:
            if 'run' not in step_data:
                raise PipelineError(f"Step in job '{job_name}' is missing a 'run' command.")
            
            step_name = step_data.get('name', step_data['run'])
            parsed_steps.append(Step(name=step_name, run=step_data['run']))

        needs = job_data.get('needs', [])
        if not isinstance(needs, list):
            raise PipelineError(f"'needs' in job '{job_name}' must be a list.")

        parsed_jobs[job_name] = Job(
            name=job_name,
            steps=parsed_steps,
            needs=needs,
            image=global_image  # NEW: Apply global image to every job
        )

    for job_name, job in parsed_jobs.items():
        for needed_job in job.needs:
            if needed_job not in parsed_jobs:
                raise PipelineError(f"Job '{job_name}' needs '{needed_job}', but '{needed_job}' does not exist.")

    return Pipeline(jobs=parsed_jobs, image=global_image)