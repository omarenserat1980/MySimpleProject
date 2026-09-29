import tempfile
import unittest
from pathlib import Path

from brain_git_platform import service
from brain_git_platform.git_transport import advertise_refs, resolve_repo_path


class GitTransportTests(unittest.TestCase):
    def test_resolve_and_advertise(self):
        with tempfile.TemporaryDirectory() as d:
            old_root, old_db = service.ROOT, service.DB
            try:
                service.ROOT = Path(d)
                service.DB = service.ROOT / "brain-git.db"
                service.initialize()
                service.create_repository(service.Repository("brain", "demo"))
                resolved = resolve_repo_path("/git/brain/demo.git")
                self.assertTrue(resolved.is_dir())
                payload = advertise_refs(resolved, "git-upload-pack")
                self.assertTrue(payload.startswith(b"# service=git-upload-pack") or payload.startswith(b"001"))
                self.assertIn(b"git-upload-pack", payload)
            finally:
                service.ROOT, service.DB = old_root, old_db


if __name__ == "__main__":
    unittest.main()