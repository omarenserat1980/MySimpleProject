"""Bridge from resolved customer feedback into the Brain TaskEngine."""

from cloud.customer_feedback import improvement_from_feedback


def enqueue_improvement(feedback, task_engine, evidence_ref=None):
    """Create a Brain TaskEngine task from verified/resolved customer feedback."""
    improvement = improvement_from_feedback(feedback, evidence_ref)
    task = task_engine.create(
        title=improvement.title,
        parent_id=feedback.feedback_id,
    )
    task.update({
        "source": "CUSTOMER_FEEDBACK",
        "feedback_id": feedback.feedback_id,
        "category": feedback.category,
        "priority": improvement.priority,
        "evidence_ref": improvement.evidence_ref,
    })
    return task
