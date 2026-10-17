import unittest

from brain_v12.brain.apm_cinematic_adapter import (
    cinematic_segment_manifest,
    segments_from_cinematic_plan,
)


class CinematicAdapterTests(unittest.TestCase):
    def test_groups_shots_without_losing_timeline(self):
        plan = {
            "version": "CINEMATIC_V3_PRO",
            "title": "Test",
            "language": "ar",
            "target_minutes": 1,
            "shots": [
                {"id": "B01-S01", "duration_s": 6, "visual": "a", "voice": "a", "camera": "PAN"},
                {"id": "B01-S02", "duration_s": 6, "visual": "b", "voice": "b", "camera": "PUSH"},
                {"id": "B01-S03", "duration_s": 9, "visual": "c", "voice": "c", "camera": "PULL"},
                {"id": "B02-S01", "duration_s": 9, "visual": "d", "voice": "d", "camera": "TRACK"},
            ],
            "continuity": {"character_bible": True},
            "quality_gates": {"reject_slideshow": True},
        }
        segments = segments_from_cinematic_plan(plan, shots_per_segment=2)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].start_s, 0.0)
        self.assertEqual(segments[0].duration_s, 12.0)
        self.assertEqual(segments[1].start_s, 12.0)
        self.assertEqual(segments[1].duration_s, 18.0)

        manifest = cinematic_segment_manifest(plan, segments)
        self.assertEqual(manifest["shot_count"], 4)
        self.assertEqual(manifest["segment_count"], 2)
        self.assertTrue(manifest["continuity"]["character_bible"])

    def test_rejects_empty_plan(self):
        with self.assertRaises(ValueError):
            segments_from_cinematic_plan({"shots": []})


if __name__ == "__main__":
    unittest.main()
