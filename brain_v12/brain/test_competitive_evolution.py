import unittest
from brain_v12.brain.competitive_evolution import REFERENCE_COMPANIES,TRACKS,PRINCIPLES

class CompetitiveEvolutionTests(unittest.TestCase):
    def test_references(self): self.assertEqual(REFERENCE_COMPANIES,("NVIDIA","Microsoft","Apple"))
    def test_tracks(self):
        self.assertGreaterEqual(len(TRACKS),8)
        for track in TRACKS: self.assertTrue(track.reference and track.target and track.evidence)
    def test_principles(self):
        self.assertIn("benchmark_before_claim",PRINCIPLES)
        self.assertIn("evidence_before_status",PRINCIPLES)

if __name__=="__main__": unittest.main()
