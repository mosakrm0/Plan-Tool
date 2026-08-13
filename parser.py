import yaml
import warnings
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

def _extract_image(image_field):
    if not image_field:
        return 'ubuntu:latest'
    if isinstance(image_field, str):
        return image_field
    if isinstance(image_field, dict):
        return image_field.get('name') or image_field.get('image') or 'ubuntu:latest'
    return 'ubuntu:latest'


def _make_step_from_run(name, run_cmd):
    return Step(name=name or run_cmd, run=run_cmd)


def load_pipeline(filepath: str) -> Pipeline:
    try:
        with open(filepath, 'r') as file:
            raw_data = yaml.safe_load(file)
    except FileNotFoundError:
        raise PipelineError(f"Could not find pipeline file: {filepath}")
    except yaml.YAMLError as e:
        raise PipelineError(f"Invalid YAML syntax: {e}")

    if not raw_data:
        raise PipelineError("Pipeline file is empty or invalid YAML.")

    parsed_jobs = {}
    # Try GitHub Actions / generic 'jobs' structure first
    if isinstance(raw_data, dict) and 'jobs' in raw_data:
        global_image = _extract_image(raw_data.get('image'))
        jobs_section = raw_data['jobs'] or {}

        for job_name, job_data in jobs_section.items():
            if not isinstance(job_data, dict):
                raise PipelineError(f"Job '{job_name}' must be a mapping/object.")

            # Determine job-level image (GitLab uses 'image', GitHub uses 'container')
            job_image = _extract_image(job_data.get('image') or job_data.get('container') or global_image)

            parsed_steps = []
            # GitHub Actions style: steps: [ { run: '...' }, { uses: '...' } ]
            if 'steps' in job_data and job_data['steps']:
                for idx, step_data in enumerate(job_data['steps']):
                    if not isinstance(step_data, dict):
                        continue
                    if 'run' in step_data:
                        step_name = step_data.get('name') or f"step-{idx}"
                        parsed_steps.append(_make_step_from_run(step_name, step_data['run']))
                    elif 'script' in step_data:  # some variants
                        step_name = step_data.get('name') or f"script-{idx}"
                        parsed_steps.append(_make_step_from_run(step_name, step_data['script']))
                    elif 'uses' in step_data:
                        # Convert 'uses' to an informational run (best-effort)
                        uses = step_data['uses']
                        step_name = step_data.get('name') or f"uses-{idx}"
                        warnings.warn(
                            f"Found 'uses' in job '{job_name}': {uses}. Converted to an informational echo step. "
                            "Actions referenced by 'uses' will NOT be executed.",
                            UserWarning
                        )
                        parsed_steps.append(_make_step_from_run(step_name, f"echo 'uses: {uses}'"))
                    else:
                        # Skip unknown step types but continue parsing
                        continue

            # GitLab style: script: [ ... ] or script: '...'
            elif 'script' in job_data:
                scripts = job_data['script']
                if isinstance(scripts, str):
                    parsed_steps.append(_make_step_from_run('script', scripts))
                elif isinstance(scripts, list):
                    for idx, s in enumerate(scripts):
                        parsed_steps.append(_make_step_from_run(f'script-{idx}', s))

            else:
                raise PipelineError(f"Job '{job_name}' must contain 'steps' (GitHub) or 'script' (GitLab) entries.")

            needs = job_data.get('needs') or job_data.get('dependencies') or []
            # Normalize needs to list of job names
            if isinstance(needs, str):
                needs = [needs]
            if needs is None:
                needs = []
            if not isinstance(needs, list):
                raise PipelineError(f"'needs' in job '{job_name}' must be a list.")

            parsed_jobs[job_name] = Job(
                name=job_name,
                steps=parsed_steps,
                needs=needs,
                image=job_image
            )

    else:
        # Fallback: Try GitLab single-file format where jobs are top-level keys (and 'stages' may exist)
        global_image = _extract_image(raw_data.get('image') if isinstance(raw_data, dict) else None)
        candidate_jobs = {}
        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                if not isinstance(value, dict):
                    continue
                # Heuristic: GitLab job entries commonly have 'script' key
                if 'script' in value or 'stage' in value or 'tags' in value:
                    candidate_jobs[key] = value

        if not candidate_jobs:
            raise PipelineError("Unrecognized pipeline format: no 'jobs' section and no GitLab-style jobs found.")

        for job_name, job_data in candidate_jobs.items():
            job_image = _extract_image(job_data.get('image') or global_image)
            parsed_steps = []
            scripts = job_data.get('script')
            if isinstance(scripts, str):
                parsed_steps.append(_make_step_from_run('script', scripts))
            elif isinstance(scripts, list):
                for idx, s in enumerate(scripts):
                    parsed_steps.append(_make_step_from_run(f'script-{idx}', s))
            else:
                raise PipelineError(f"Job '{job_name}' must contain 'script' entries in GitLab-style pipeline.")

            needs = job_data.get('needs') or job_data.get('dependencies') or []
            if isinstance(needs, str):
                needs = [needs]
            if needs is None:
                needs = []
            if not isinstance(needs, list):
                raise PipelineError(f"'needs' in job '{job_name}' must be a list.")

            parsed_jobs[job_name] = Job(name=job_name, steps=parsed_steps, needs=needs, image=job_image)

    # Validate cross-job needs
    for job_name, job in parsed_jobs.items():
        for needed_job in job.needs:
            if needed_job not in parsed_jobs:
                raise PipelineError(f"Job '{job_name}' needs '{needed_job}', but '{needed_job}' does not exist.")

    return Pipeline(jobs=parsed_jobs, image=global_image)