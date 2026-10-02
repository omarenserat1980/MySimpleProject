import unittest
from brain_v12.brain.level_report import current_report

class LevelReportTests(unittest.TestCase):
    def test_report(self):
        r=current_report()
        self.assertEqual(r.references,("NVIDIA","Microsoft","Apple"))
        self.assertGreaterEqual(r.benchmark_tracks,8)
        self.assertGreaterEqual(r.operating_units,7)
        self.assertGreaterEqual(r.lifecycle_stages,10)
        self.assertGreaterEqual(r.truth_rules,4)
        self.assertEqual(r.status,"ARCHITECTURE_DEFINED")

if __name__=="__main__": unittest.main()
