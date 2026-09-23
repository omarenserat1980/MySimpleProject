from brain_v7.braincore_v2.job_lifecycle import JobLifecycle


def test_job_lifecycle_transitions_and_terminal_guard():
    jobs = JobLifecycle()
    job = jobs.create("produce a video")
    jobs.transition(job.job_id, "RUNNING")
    assert jobs.jobs[job.job_id].attempts == 1
    jobs.transition(job.job_id, "COMPLETED", result={"quality": 0.9})
    try:
        jobs.transition(job.job_id, "RUNNING")
    except ValueError:
        pass
    else:
        raise AssertionError("terminal job was allowed to transition")
