import tempfile, unittest
from pathlib import Path
from .service import BrainGitService, BrainGitError
from .file_browser import BrainGitFileBrowser

class BrainGitServiceTests(unittest.TestCase):
    def test_repository_lifecycle_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainGitService(Path(d))
            r=s.create_repository("proof")
            self.assertEqual(r["name"],"proof")
            self.assertEqual(s.repository("proof")["name"],"proof")
            self.assertTrue(s.fsck("proof")["ok"])
            browser=BrainGitFileBrowser(s)
            self.assertIn("README.md",browser.tree("proof","main"))
            self.assertEqual(browser.file("proof","README.md","main")["content"],"Brain Git proof")
            self.assertEqual(len(s.audit("proof")),1)
            out=s.commit_files("proof",{"README.md":"Brain Git proof\\n"},"initial proof","main")
            self.assertEqual(len(out["sha"]),40)
            self.assertEqual(s.read_file_at("proof","README.md","main").rstrip("\\n"),"Brain Git proof")
            s.create_branch("proof","test-branch","main")
            self.assertTrue(any(x["name"]=="test-branch" for x in s.branches("proof")))
            self.assertTrue(s.fsck("proof")["ok"])
    def test_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainGitService(d); s.create_repository("x")
            with self.assertRaises(BrainGitError):s.create_repository("x")

if __name__=="__main__": unittest.main()
