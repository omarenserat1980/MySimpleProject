from platform_foundation.apm import APM
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.brain_ci_executor import BrainCIExecutor
from platform_foundation.open_source_gate import OpenSourceCandidate, OpenSourceGate
from platform_foundation.stage_orchestrator import StageOrchestrator


class FakeStore:
    def __init__(self):
        self.data = {}
    def get(self, key):
        return self.data.get(key)
    def set(self, key, value):
        self.data[key] = value


def test_pipeline_blocks_before_first_stage_when_open_source_is_blocked(tmp_path):
    store = FakeStore()
    orchestrator = StageOrchestrator(store)
    executor = BrainCIExecutor(store=store, executor_id="brain-local-01", persistent=True)
    blocked = OpenSourceCandidate(
        "unreviewed-component", "global", "Apache-2.0", "1.0.0",
        True, False, True, True,
    )
    pipeline = AutonomousPipeline(
        orchestrator,
        APM(store=store),
        ci_executor=executor,
        open_source_gate=OpenSourceGate(),
        open_source_candidates=[blocked],
    )

    calls = {"execute": 0}

    def execute(_):
        calls["execute"] += 1

    result = pipeline.run_until(
        execute=execute,
        verify=lambda *_: True,
        stop_stage=1,
    )

    assert result.status == "BLOCKED"
    assert calls["execute"] == 0
    assert pipeline.health()["open_source"]["status"] == "BLOCKED"
