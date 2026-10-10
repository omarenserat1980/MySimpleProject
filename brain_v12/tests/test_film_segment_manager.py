import tempfile
import unittest

from brain_v12.brain.film_segment_manager import FilmSegmentManager


class FilmSegmentManagerTests(unittest.TestCase):
    def test_plans_stable_30_second_segments(self):
        segments = FilmSegmentManager(segment_duration_s=30).plan(75)
        self.assertEqual(len(segments), 3)
        self.assertEqual([(s.start_s, s.duration_s) for s in segments],
                         [(0.0, 30.0), (30.0, 30.0), (60.0, 15.0)])

    def test_runs_and_returns_timeline_order(self):
        manager = FilmSegmentManager(segment_duration_s=30, max_workers=2, retry_limit=0)
        segments = manager.plan(75)
        executed = []

        def execute(segment):
            executed.append(segment.id)
            return {"ok": True, "output": segment.id}

        def verify(segment, result):
            return {"verified": result["ok"], "evidence_ref": f"segment://{segment.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = manager.run(segments, td, execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["assembly_order"],
                         ["SEG-0001", "SEG-0002", "SEG-0003"])
        self.assertEqual(len(executed), 3)
        self.assertTrue(result["ready_for_assembly"])

    def test_segment_failure_blocks_assembly(self):
        manager = FilmSegmentManager(segment_duration_s=30, max_workers=2, retry_limit=0)
        segments = manager.plan(60)

        def execute(segment):
            return {"ok": segment.index == 0}

        def verify(segment, result):
            return {"verified": result["ok"], "evidence_ref": f"segment://{segment.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = manager.run(segments, td, execute, verify)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["ready_for_assembly"])


if __name__ == "__main__":
    unittest.main()
