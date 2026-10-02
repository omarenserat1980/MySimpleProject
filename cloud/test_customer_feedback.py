from cloud.customer_feedback import FeedbackState, FeedbackStore

def test_feedback_lifecycle_and_evidence(tmp_path):
    s=FeedbackStore(tmp_path)
    f=s.create(customer_id="c1",rating=4,category="QUALITY",body="good but slow")
    f.transition(FeedbackState.TRIAGED,"brain")
    f.assign("product")
    f.transition(FeedbackState.IN_PROGRESS,"product")
    try: f.transition(FeedbackState.RESOLVED,"product")
    except ValueError: pass
    else: raise AssertionError("resolution without evidence must fail")
    f.transition(FeedbackState.RESOLVED,"product","case://feedback/1")
    s.save(f)
    g=s.get(f.feedback_id)
    assert g.state is FeedbackState.RESOLVED
    assert len(g.events)==6
    assert [e["event"] for e in g.events] == ["CREATED","STATE_CHANGED","STATE_CHANGED","ASSIGNED","STATE_CHANGED","STATE_CHANGED"]

def test_invalid_rating(tmp_path):
    try: FeedbackStore(tmp_path).create(customer_id=None,rating=6,category="X",body="bad")
    except ValueError: pass
    else: raise AssertionError("invalid rating accepted")


def test_resolved_feedback_creates_improvement_task(tmp_path):
    from cloud.customer_feedback import improvement_from_feedback
    s=FeedbackStore(tmp_path)
    f=s.create(customer_id="c1",rating=2,category="RELIABILITY",body="failed twice")
    f.transition(FeedbackState.TRIAGED,"brain")
    f.transition(FeedbackState.IN_PROGRESS,"brain")
    f.transition(FeedbackState.RESOLVED,"brain","case://verified")
    task=improvement_from_feedback(f)
    assert task.feedback_id == f.feedback_id
    assert task.priority == "HIGH"
    assert task.evidence_ref == "case://verified"


def test_feedback_task_bridge_uses_task_engine(tmp_path):
    from cloud.feedback_task_bridge import enqueue_improvement
    from brain_v12.brain.task_engine import TaskEngine
    s=FeedbackStore(tmp_path)
    f=s.create(customer_id="c1",rating=2,category="RELIABILITY",body="failure")
    f.transition(FeedbackState.TRIAGED,"brain")
    f.transition(FeedbackState.IN_PROGRESS,"brain")
    f.transition(FeedbackState.RESOLVED,"brain","case://verified")
    engine=TaskEngine()
    task=enqueue_improvement(f,engine)
    assert task["source"] == "CUSTOMER_FEEDBACK"
    assert task["feedback_id"] == f.feedback_id
    assert task["status"] == "PENDING"
    assert engine.ready()[0]["id"] == task["id"]
