import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from brain_v12.brain.film_supervisor import FilmSupervisor


class FilmSupervisorGoldenGateTests(unittest.TestCase):
    def test_artifact_readiness_is_not_reported_as_verified_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "film-work"
            artifacts = root / "artifacts"
            supervisor = FilmSupervisor(work=str(work), artifact_root=str(artifacts))

            with patch(
                "brain_v12.brain.film_supervisor.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stderr="", stdout=""),
            ), patch.object(supervisor, "verify", return_value=(True, {"fixture": True})):
                result = supervisor.run(seconds=1, fps=1)

            manifest = json.loads((work / "film_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(manifest["status"], "BLOCKED_GOLDEN_ACCEPTANCE")
            self.assertFalse(manifest["verified"])
            self.assertFalse((work / "VERIFIED_COMPLETED").exists())


    def test_independently_verified_simulated_artifact_closes_golden_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "film-work"
            artifacts = root / "artifacts"
            supervisor = FilmSupervisor(work=str(work), artifact_root=str(artifacts))
            independent = {
                "reality_level": "SIMULATED",
                "video": True,
                "audio": True,
                "duration": 1.0,
                "size": 2048,
                "sha256": "a" * 64,
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
            }
            with patch(
                "brain_v12.brain.film_supervisor.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stderr="", stdout=""),
            ), patch.object(supervisor, "verify", return_value=(True, {"fixture": True})), patch.object(
                supervisor, "verify_independently", return_value=(True, independent)
            ):
                result = supervisor.run(seconds=1, fps=1)

            manifest = json.loads((work / "film_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(manifest["status"], "VERIFIED_COMPLETED")
            self.assertTrue(manifest["verified"])
            self.assertTrue((work / "VERIFIED_COMPLETED").exists())
            events = [
                json.loads(line)
                for line in (artifacts / "supervisor" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            gate_events = [row for row in events if row.get("event") == "golden_acceptance_gate"]
            self.assertTrue(gate_events)
            self.assertTrue(gate_events[-1]["data"]["accepted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
