import tempfile
import unittest

from brain_v12.brain.apm_chunk_scheduler import Chunk, ChunkScheduler


class ChunkSchedulerTests(unittest.TestCase):
    def test_parallel_chunks_and_resume(self):
        chunks = [Chunk(f"C{i}", "VIDEO", i, "v1") for i in range(4)]
        calls = []

        def execute(chunk):
            calls.append(chunk.id)
            return {"ok": True, "output": chunk.id}

        def verify(chunk, result):
            return {"verified": result["ok"], "evidence_ref": f"chunk://{chunk.id}"}

        with tempfile.TemporaryDirectory() as td:
            first = ChunkScheduler(chunks, td, max_workers=2, retry_limit=0).run(execute, verify)
            second = ChunkScheduler(chunks, td, max_workers=2, retry_limit=0).run(execute, verify)

        self.assertEqual(first["status"], "VERIFIED_COMPLETED")
        self.assertEqual(second["status"], "VERIFIED_COMPLETED")
        self.assertEqual(calls, [f"C{i}" for i in range(4)])

    def test_failed_chunk_retries_only_itself(self):
        chunks = [Chunk("A", "VIDEO", 0), Chunk("B", "VIDEO", 1)]
        attempts = {"A": 0, "B": 0}

        def execute(chunk):
            attempts[chunk.id] += 1
            return {"ok": chunk.id == "A" and attempts[chunk.id] == 2 or chunk.id == "B"}

        def verify(chunk, result):
            return {"verified": result["ok"], "evidence_ref": f"chunk://{chunk.id}"}

        with tempfile.TemporaryDirectory() as td:
            result = ChunkScheduler(chunks, td, max_workers=2, retry_limit=1).run(execute, verify)

        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(attempts["A"], 2)
        self.assertEqual(attempts["B"], 1)


if __name__ == "__main__":
    unittest.main()
