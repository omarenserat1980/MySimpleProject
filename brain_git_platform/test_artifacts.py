import tempfile, unittest
from brain_git_platform.storage.artifacts import ArtifactStore
class ArtifactTests(unittest.TestCase):
    def test_content_addressed_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            s=ArtifactStore(d)
            meta=s.put("run1","result.json",b"ok")
            self.assertEqual(meta["size"],2)
            self.assertEqual(s.get("run1","result.json"),b"ok")
            self.assertEqual(len(meta["sha256"]),64)
if __name__ == "__main__": unittest.main()
