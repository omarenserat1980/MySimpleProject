from pathlib import Path

from brain_v7.braincore_v2.benchmark_router import (
    choose_backend,
    load_state,
    record_observation,
    save_state,
)


def _shot():
    return {"shot_id": "S1", "role": "PERFORMANCE"}


def test_benchmark_learns_latency_without_bypassing_quality_floor():
    state = load_state(Path("/tmp/nonexistent-electronic-brain-benchmark.json"))
    for _ in range(3):
        record_observation(state, _shot(), "wan", latency_s=10, success=True, qc_score=0.93)
        record_observation(state, _shot(), "ltx", latency_s=5, success=True, qc_score=0.70)
    assert choose_backend(_shot(), ["wan", "ltx"], state=state, quality_floor=0.82) == "wan"


def test_unknown_backend_is_explored_deterministically():
    state = {"version": 1, "observations": {}, "updated_at": 0}
    assert choose_backend(_shot(), ["wan", "ltx"], state=state) == "ltx"
    assert choose_backend(_shot(), ["ltx", "wan"], state=state) == "ltx"


def test_benchmark_state_persists(tmp_path: Path):
    path = tmp_path / "benchmark.json"
    state = load_state(path)
    record_observation(state, _shot(), "wan", latency_s=2.5, success=True, qc_score=0.91)
    save_state(state, path)
    restored = load_state(path)
    assert restored["observations"]
    assert next(iter(restored["observations"].values()))["samples"] == 1
