from .brain_review_loop import review_and_request
from .cinema_engine_v6 import CinemaEngineV6


def test_brain_review_is_auditable():
    result = review_and_request(CinemaEngineV6().snapshot())
    assert result["proposals"]
    assert result["implemented"]["CONTINUITY_FIRST"] is True
    assert result["implemented"]["SHOT_BENCHMARK"] is True
