import unittest
from unittest.mock import patch

from brain_v12.brain.video_generation_adapter import ComfyUIVideoAdapter, VideoGenerationError


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return self.payload


class VideoAdapterTests(unittest.TestCase):
    def test_probe_reports_unavailable_without_server(self):
        adapter = ComfyUIVideoAdapter("http://127.0.0.1:9")
        report = adapter.probe()
        self.assertFalse(report["available"])

    def test_submit_requires_prompt_id(self):
        adapter = ComfyUIVideoAdapter()
        with patch.object(adapter.api, "system_stats", return_value={}):
            with patch.object(adapter.api, "queue_prompt", return_value={}):
                with self.assertRaises(VideoGenerationError):
                    adapter.submit({"1": {"class_type": "Test"}})

    def test_find_video_accepts_comfyui_video_output(self):
        item = {"outputs": {"7": {"gifs": [{"filename": "scene.mp4", "subfolder": "", "type": "output"}]}}}
        self.assertEqual(ComfyUIVideoAdapter._find_video(item["outputs"])["filename"], "scene.mp4")


if __name__ == "__main__":
    unittest.main()
