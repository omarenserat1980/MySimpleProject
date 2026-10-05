import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.apm_film_assembly import FilmAssemblyGate, SegmentArtifact


class FilmAssemblyGateTests(unittest.TestCase):
    def test_incomplete_segments_are_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "seg.mp4"
            p.write_bytes(b"x")
            result = FilmAssemblyGate(td).assemble(
                film_id="film-1",
                expected_segments=2,
                verified_segments=[SegmentArtifact("SEG-0001", 0, str(p), 30.0)],
                assembler=lambda *_: {"status": "VERIFIED_COMPLETED"},
                master_qc=lambda _: {"accepted": True},
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "SEGMENT_EVIDENCE_INCOMPLETE")

    def test_qc_rejection_prevents_final_completion(self):
        with tempfile.TemporaryDirectory() as td:
            items = []
            for i in range(2):
                p = Path(td) / ("seg-%d.mp4" % i)
                p.write_bytes(b"x")
                items.append(SegmentArtifact("SEG-%04d" % (i + 1), i, str(p), 30.0))
            result = FilmAssemblyGate(td).assemble(
                film_id="film-1",
                expected_segments=2,
                verified_segments=items,
                assembler=lambda *_: {"status": "VERIFIED_COMPLETED"},
                master_qc=lambda _: {"accepted": False, "reason": "QUALITY"},
            )
        self.assertEqual(result["status"], "MASTER_QC_REJECTED")


if __name__ == "__main__":
    unittest.main()
