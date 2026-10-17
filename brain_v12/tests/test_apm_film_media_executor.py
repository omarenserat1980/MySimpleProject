import tempfile
import unittest

from brain_v12.brain.apm_film_media_executor import APMFilmMediaExecutor
from brain_v12.brain.film_segment_manager import FilmSegment


class Runner:
    def __init__(self):
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "VERIFIED_COMPLETED", "output": "segment.mp4"}


class Pipeline:
    def __init__(self):
        self.runner = Runner()


class FilmMediaExecutorTests(unittest.TestCase):
    def test_authorization_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            result = APMFilmMediaExecutor(Pipeline(), state_dir=td).run(
                [FilmSegment("S1", 0, 0, 10)], authorized=False)
        self.assertEqual(result["status"], "AUTHORIZATION_REQUIRED")

    def test_verified_media_segment_produces_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            pipeline = Pipeline()
            result = APMFilmMediaExecutor(Pipeline(), state_dir=td, max_workers=1).run(
                [FilmSegment("S1", 0, 0, 10)], authorized=True)
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertTrue(result["ready_for_assembly"])
        self.assertEqual(len(result["segments"]), 1)


if __name__ == "__main__":
    unittest.main()
