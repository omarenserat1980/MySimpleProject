import pathlib
import shutil
import subprocess
import time
import unittest

from brain_v12 import media_engine


class MediaEngineTests(unittest.TestCase):
    def test_safe_path_rejects_traversal(self):
        with self.assertRaises(ValueError):
            media_engine._safe_name("../secret.mp4")
        with self.assertRaises(ValueError):
            media_engine._safe_name("/absolute.mp4")

    def test_runtime_tools_available_in_ci(self):
        self.assertTrue(shutil.which("ffmpeg"), "ffmpeg is required by BRAIN Media Engine")
        self.assertTrue(shutil.which("ffprobe"), "ffprobe is required by BRAIN Media Engine")

    def test_convert_smoke(self):
        name = "brain-media-ci-input.mp4"
        source = media_engine.MEDIA_ROOT / name
        source.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=320x180:r=15",
                    "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
                ],
                check=True,
                timeout=30,
            )
            job = media_engine.submit("convert", {
                "input": name, "width": 320, "height": 180, "fps": 15,
                "format": "mp4",
            })
            deadline = time.time() + 30
            final = job
            while time.time() < deadline:
                final = media_engine.snapshot(job["job_id"])
                if final["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
                    break
                time.sleep(0.2)
            self.assertEqual(final["status"], "COMPLETED", final)
            self.assertTrue(final["qc"]["probe_ok"], final)
            output = media_engine.OUTPUT_ROOT / pathlib.Path(final["result"]["outputs"][0]).name
            self.assertTrue(output.exists(), output)
            output.unlink(missing_ok=True)
        finally:
            source.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
