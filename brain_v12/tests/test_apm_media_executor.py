import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brain_v12.brain.apm_media_executor import APMMediaExecutor


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs["kind"])
        return {
            "status": "VERIFIED_COMPLETED",
            "output": {"path": f"/tmp/{kwargs['kind']}.out"},
        }


class FakeRegistry:
    pass


class APMMediaExecutorTests(unittest.TestCase):
    def _pipeline(self, runner):
        stages = (
            SimpleNamespace(name="IMAGE", kind="image", prompt="i", output_format="png", depends_on=()),
            SimpleNamespace(name="VOICE", kind="audio", prompt="v", output_format="mp3", depends_on=()),
            SimpleNamespace(name="VIDEO", kind="video", prompt="x", output_format="mp4", depends_on=("IMAGE", "VOICE")),
        )
        return SimpleNamespace(
            pipeline_id="p1",
            runner=runner,
            registry=FakeRegistry(),
            stages=stages,
        )

    def test_executes_fanout_then_join(self):
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as td:
            result = APMMediaExecutor(
                self._pipeline(runner), state_dir=td, max_workers=2, retry_limit=0
            ).run(authorized=True, quality_scores={
                "IMAGE": {"technical_validity": 1},
                "VOICE": {"technical_validity": 1},
                "VIDEO": {"technical_validity": 1},
            }, minimum_quality=0.1)
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(sorted(runner.calls), ["audio", "image", "video"])

    def test_cached_outputs_are_restored_for_dependents(self):
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            for name, kind in (("IMAGE", "image"), ("VOICE", "audio")):
                record = {
                    "stage_id": name,
                    "status": "VERIFIED_COMPLETED",
                    "fingerprint": "",
                    "result": {"status": "VERIFIED_COMPLETED", "output": {"path": f"/cache/{name}"}},
                    "evidence_ref": f"media://p1/{name}",
                }
                (state / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")

            pipeline = self._pipeline(runner)
            executor = APMMediaExecutor(pipeline, state_dir=td, max_workers=1, retry_limit=0)
            result = executor.run(authorized=True, quality_scores={
                "IMAGE": {"technical_validity": 1},
                "VOICE": {"technical_validity": 1},
                "VIDEO": {"technical_validity": 1},
            }, minimum_quality=0.1)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(runner.calls, ["video"])


if __name__ == "__main__":
    unittest.main()
