import pathlib
import shutil
import subprocess
import time
import unittest

from brain_v12 import media_engine


class MediaEngineTests(unittest.TestCase):
    def _wait(self, job_id, timeout=45):
        deadline = time.time() + timeout
        final = media_engine.snapshot(job_id)
        while time.time() < deadline:
            final = media_engine.snapshot(job_id)
            if final["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
                return final
            time.sleep(0.2)
        return final

    def test_safe_path_rejects_traversal(self):
        with self.assertRaises(ValueError):
            media_engine._safe_name("../secret.mp4")
        with self.assertRaises(ValueError):
            media_engine._safe_name("/absolute.mp4")

    def test_runtime_tools_available_in_ci(self):
        self.assertTrue(shutil.which("ffmpeg"))
        self.assertTrue(shutil.which("ffprobe"))

    def test_timeline_command_is_allowlisted(self):
        self.assertIn("timeline", {"probe", "convert", "concat", "extract-audio", "extract-frames", "slideshow", "trim", "mix-audio", "fade", "timeline"})
        with self.assertRaises(ValueError):
            media_engine._validate_transition("rm -rf")
        with self.assertRaises(ValueError):
            media_engine._drawtext_escape("x" * 301)

    def test_convert_smoke(self):
        name = "brain-media-ci-input.mp4"
        source = media_engine.MEDIA_ROOT / name
        source.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=black:s=320x180:r=15","-t","1","-c:v","libx264","-pix_fmt","yuv420p",str(source)],check=True,timeout=30)
            job = media_engine.submit("convert", {"input":name,"width":320,"height":180,"fps":15,"format":"mp4"})
            final = self._wait(job["job_id"])
            self.assertEqual(final["status"], "COMPLETED", final)
            self.assertTrue(final["qc"]["probe_ok"], final)
            output = media_engine.OUTPUT_ROOT / pathlib.Path(final["result"]["outputs"][0]).name
            output.unlink(missing_ok=True)
        finally:
            source.unlink(missing_ok=True)

    def test_timeline_smoke(self):
        names = ["brain-timeline-a.mp4", "brain-timeline-b.mp4"]
        try:
            for color, name in [("black", names[0]), ("white", names[1])]:
                subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i",f"color=c={color}:s=320x180:r=15","-t","1","-c:v","libx264","-pix_fmt","yuv420p",str(media_engine.MEDIA_ROOT/name)],check=True,timeout=30)
            job = media_engine.submit("timeline", {
                "scenes": [{"input":names[0],"start":0,"duration":1,"caption":"BRAIN"},{"input":names[1],"start":0,"duration":1}],
                "transition":"fade",
                "transition_duration":0.25,
                "crf":24
            })
            final = self._wait(job["job_id"], 60)
            self.assertEqual(final["status"], "COMPLETED", final)
            self.assertTrue(final["qc"]["probe_ok"], final)
            output = media_engine.OUTPUT_ROOT / pathlib.Path(final["result"]["outputs"][0]).name
            output.unlink(missing_ok=True)
        finally:
            for name in names:
                (media_engine.MEDIA_ROOT/name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
