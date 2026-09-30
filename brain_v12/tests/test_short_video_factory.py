import unittest

from brain_v12.short_video_factory import (
    build_plan,
    estimate_duration,
    word_timing,
    backend_status,
    registry,
)


class ShortVideoFactoryTests(unittest.TestCase):
    def test_duration_is_bounded(self):
        self.assertGreaterEqual(estimate_duration("مرحباً BRAIN"), 1.5)
        self.assertLessEqual(estimate_duration("x " * 1000), 60.0)

    def test_word_timing_covers_duration(self):
        timing = word_timing("مرحباً أنا BRAIN", 4.0)
        self.assertEqual(len(timing), 3)
        self.assertEqual(timing[-1]["end"], 4.0)
        self.assertLess(timing[0]["start"], timing[0]["end"])

    def test_vertical_plan_defaults_to_free_local_timing(self):
        plan = build_plan(
            "مرحباً، أنا BRAIN، وسأساعدك في صنع أفكار رائعة!",
            "/media/brain-cat.png",
        )
        self.assertEqual(plan["width"], 1080)
        self.assertEqual(plan["height"], 1920)
        self.assertEqual(plan["fps"], 30)
        self.assertEqual(plan["lipsync_backend"], "local-timing")
        self.assertEqual(plan["tts_backend"], "none")

    def test_registry_records_license_provenance(self):
        names = {x["name"] for x in registry()}
        self.assertIn("MuseTalk", names)
        self.assertIn("VOICEVOX Core", names)
        for item in registry():
            self.assertTrue(item["license"])
            self.assertTrue(item["source"])

    def test_backend_status_has_local_gate(self):
        status = backend_status()
        self.assertIn("free_local_ready", status)
        self.assertIn("ffmpeg", status["commands"])


if __name__ == "__main__":
    unittest.main()
