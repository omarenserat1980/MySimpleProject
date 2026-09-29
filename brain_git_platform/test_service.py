import tempfile
from pathlib import Path
import os
import unittest

class ServiceTests(unittest.TestCase):
    def test_native_repo_creation_has_no_github_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["BRAIN_GIT_ROOT"] = d
            from service import Repository, create_repository, health
            p = create_repository(Repository("brain", "test"))
            self.assertTrue((Path(p) / "HEAD").exists())
            self.assertTrue(health()["ok"])
            self.assertFalse(health()["github_dependency"])

if __name__ == "__main__":
    unittest.main()
