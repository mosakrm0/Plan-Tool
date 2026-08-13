from parser import Pipeline, PipelineError

def get_execution_order(pipeline: Pipeline) -> list:
    """
    Takes a parsed Pipeline object and returns a list of job names 
    in the correct topological execution order.
    """
    jobs_dict = pipeline.jobs
    
    # 1. Track how many dependencies each job is still waiting on (in-degree)
    in_degree = {job_name: 0 for job_name in jobs_dict}
    
    # 2. Track which jobs are unlocked when a specific job finishes (adjacency list)
    unlocks = {job_name: [] for job_name in jobs_dict}

    # 3. Build the graph relationships
    for job_name, job in jobs_dict.items():
        for needed_job in job.needs:
            # We already validated missing needs in parser.py, but graph logic relies on it
            unlocks[needed_job].append(job_name)
            in_degree[job_name] += 1

    # 4. Find all jobs that have zero dependencies to start
    ready_queue = [job_name for job_name in jobs_dict if in_degree[job_name] == 0]
    execution_order = []

    # 5. Process the queue
    while ready_queue:
        # Take a ready job off the queue
        current_job = ready_queue.pop(0)
        execution_order.append(current_job)

        # Look at the jobs that were waiting on this one to finish
        for dependent_job in unlocks[current_job]:
            in_degree[dependent_job] -= 1  # Cross one dependency off their list
            if in_degree[dependent_job] == 0:
                ready_queue.append(dependent_job) # If they have no more dependencies, they are ready!

    # 6. Cycle Detection
    # If we processed everything, the execution list length will match the total jobs.
    if len(execution_order) != len(jobs_dict):
        raise PipelineError("Cycle detected in job dependencies! (e.g., job A needs B, and B needs A)")

    return execution_order


