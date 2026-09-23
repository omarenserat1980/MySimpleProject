from brain_v7.braincore_v2.autonomous_task import AutonomousTask


def test_autonomous_task_has_brain_and_job_lifecycle():
    task = AutonomousTask()
    assert task.brain is not None
    assert task.jobs is not None
