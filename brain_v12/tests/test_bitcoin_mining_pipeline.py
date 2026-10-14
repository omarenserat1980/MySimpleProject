from brain_v12.brain.bitcoin_mining_pipeline import STAGES, PipelineState, prerequisite_for


def test_pipeline_is_strictly_sequential():
    state = PipelineState()
    for stage in STAGES:
        assert state.next_stage() == stage
        state.advance(stage)
    assert state.next_stage() is None
    assert state.snapshot()["revenue_realized"] is True


def test_late_stage_cannot_skip_prerequisites():
    state = PipelineState()
    try:
        state.advance("BTC_RECEIVED")
    except RuntimeError as exc:
        assert str(exc) == "prerequisite_stage_missing"
    else:
        raise AssertionError("late stage must not bypass prerequisites")


def test_prerequisites_are_ordered():
    assert prerequisite_for("WORKER_AUTHORIZED") == "SOFTWARE_READY"
    assert prerequisite_for("SHA256D_EXECUTION") == "WORKER_AUTHORIZED"
    assert prerequisite_for("REVENUE_REALIZED") == "BTC_RECEIVED"
