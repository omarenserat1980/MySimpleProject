import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from brain_v12.brain import film_supervisor as film_module
from brain_v12.brain.brain_supervisor import BrainSupervisor as RealBrainSupervisor


class FilmSupervisorEvidenceTests(unittest.TestCase):
    def test_verified_artifact_records_runtime_evidence_before_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            instances = []

            def supervisor_factory(path, max_cycles):
                supervisor = RealBrainSupervisor(path, max_cycles)
                supervisor.resource_guard.sample = lambda: {"emergency": False}
                supervisor.execution_gateway.authorize = lambda action: {"allowed": True}
                instances.append(supervisor)
                return supervisor

            def fake_run(command, **kwargs):
                if command[:2] == ["python", "cloud/last_light_movie.py"]:
                    output_dir = Path(command[command.index("--output") + 1])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    (output_dir / "last_light_city.mp4").write_bytes(b"test-mp4")
                    return CompletedProcess(command, 0, stdout="rendered", stderr="")
                if command[0] == "ffprobe":
                    payload = {
                        "streams": [
                            {"codec_type": "video", "codec_name": "h264", "width": 16, "height": 9},
                            {"codec_type": "audio", "codec_name": "aac"},
                        ],
                        "format": {"duration": "1.0", "size": "8"},
                    }
                    return CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
                raise AssertionError(f"unexpected subprocess: {command}")

            supervisor = film_module.FilmSupervisor(
                work=str(root / "work"), artifact_root=str(root / "artifacts"), max_attempts=1
            )
            with patch.object(film_module, "BrainSupervisor", side_effect=supervisor_factory), patch.object(
                film_module.subprocess, "run", side_effect=fake_run
            ):
                result = supervisor.run(seconds=1, fps=1)

            self.assertEqual(result, 0)
            self.assertTrue((root / "work" / "VERIFIED_COMPLETED").is_file())
            self.assertEqual(json.loads((root / "work" / "film_manifest.json").read_text())["status"], "VERIFIED_COMPLETED")
            self.assertEqual(len(instances), 1)
            brain = instances[0]
            state = json.loads((root / "artifacts" / "supervisor" / "state.json").read_text())
            self.assertEqual(state["job"]["phase"], "deliver")
            self.assertEqual(state["job"]["status"], "completed")
            evidence = brain.verify_evidence(state["job"]["job_id"], required_kind="film_artifact_verified")
            self.assertTrue(evidence.verified, evidence.reasons)
            self.assertTrue(evidence.evidence_ids)

    def test_missing_artifact_cannot_be_reported_as_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor = film_module.FilmSupervisor(work=directory, artifact_root=str(Path(directory) / "artifacts"))
            ok, details = supervisor.verify()
            self.assertFalse(ok)
            self.assertEqual(details["reason"], "missing_or_empty_mp4")


if __name__ == "__main__":
    unittest.main()
