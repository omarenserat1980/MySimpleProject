from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from brain_git_platform import service
from brain_git_platform.runner.worker import execute_queued_run
from brain_git_platform.workflows import dispatch


class WorkerTests(unittest.TestCase):
    def test_queued_run_checks_out_native_repository(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "brain"
            old_root, old_db = service.ROOT, service.DB
            service.ROOT, service.DB = root, root / "brain-git.db"
            try:
                bare = service.create_repository(service.Repository("brain", "demo"))
                seed = Path(d) / "seed"
                subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "brain@test.local"], cwd=seed, check=True)
                subprocess.run(["git", "config", "user.name", "Brain Test"], cwd=seed, check=True)
                (seed / "README").write_text("native\n", encoding="utf-8")
                subprocess.run(["git", "add", "README"], cwd=seed, check=True)
                subprocess.run(["git", "commit", "-m", "seed"], cwd=seed, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=seed, check=True, capture_output=True)

                manifest = seed / "brain_git_platform" / "workflows"
                manifest.mkdir(parents=True)
                (manifest / "brain-git-foundation.json").write_text(
                    '{"name":"worker","steps":[{"name":"check","command":["python","-c","print(\'native-runner-ok\')"]}]}',
                    encoding="utf-8",
                )
                subprocess.run(["git", "add", "."], cwd=seed, check=True)
                subprocess.run(["git", "commit", "-m", "workflow"], cwd=seed, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=seed, check=True, capture_output=True)

                run = dispatch("brain", "demo", "worker", "main")
                result = execute_queued_run(run.id)
                self.assertEqual(result["status"], "success")
            finally:
                service.ROOT, service.DB = old_root, old_db


if __name__ == "__main__":
    unittest.main()
