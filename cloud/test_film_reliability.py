import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cloud.film_reliability import FilmReliabilityEngine


class FilmReliabilityTests(unittest.TestCase):
    def test_no_success_without_verified_audio_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = FilmReliabilityEngine(Path(tmp), max_attempts=1)
            fake = Path(tmp) / ".attempts" / "attempt-1" / "final.mp4"
            fake.parent.mkdir(parents=True)
            fake.write_bytes(b"x" * 2048)
            with patch.object(engine, "_qc", return_value={"ok": False, "error": "media_qc_failed"}),                  patch("cloud.film_reliability.subprocess.run") as run:
                run.return_value.returncode = 0
                result = engine.run({"title": "test", "target_minutes": 1})
            self.assertFalse(result["ok"])
            self.assertFalse((Path(tmp) / "final.mp4").exists())
            self.assertFalse((Path(tmp) / "film_manifest.json").exists())

    def test_success_requires_qc_then_promotes_atomic_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = FilmReliabilityEngine(Path(tmp), max_attempts=1)
            def qc(path):
                if Path(path).exists():
                    return {"ok": True, "duration": 1.0, "size": Path(path).stat().st_size}
                return {"ok": False}
            def fake_run(cmd, **kwargs):
                attempt = Path(tmp) / ".attempts" / "attempt-1"
                attempt.mkdir(parents=True, exist_ok=True)
                (attempt / "final.mp4").write_bytes(b"verified" * 512)
                class P: returncode = 0
                return P()
            with patch.object(engine, "_qc", side_effect=qc), patch("cloud.film_reliability.subprocess.run", side_effect=fake_run):
                result = engine.run({"title": "test", "target_minutes": 1})
            self.assertTrue(result["ok"])
            self.assertTrue(Path(result["video_path"]).is_file())
            manifest = json.loads(Path(result["manifest_path"]).read_text())
            self.assertEqual(manifest["status"], "VERIFIED_COMPLETED")


if __name__ == "__main__":
    unittest.main()
