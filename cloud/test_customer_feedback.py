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
    assert len(g.events)==5

def test_invalid_rating(tmp_path):
    try: FeedbackStore(tmp_path).create(customer_id=None,rating=6,category="X",body="bad")
    except ValueError: pass
    else: raise AssertionError("invalid rating accepted")
