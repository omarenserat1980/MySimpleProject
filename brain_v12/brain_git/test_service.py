import tempfile, unittest
from pathlib import Path
from .service import BrainGitService, BrainGitError

class BrainGitServiceTests(unittest.TestCase):
    def test_repository_lifecycle_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainGitService(Path(d))
            r=s.create_repository("proof")
            self.assertEqual(r["name"],"proof")
            self.assertEqual(s.repository("proof")["name"],"proof")
            self.assertTrue(s.fsck("proof")["ok"])
            self.assertEqual(len(s.audit("proof")),1)
    def test_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainGitService(d); s.create_repository("x")
            with self.assertRaises(BrainGitError):s.create_repository("x")

if __name__=="__main__": unittest.main()
