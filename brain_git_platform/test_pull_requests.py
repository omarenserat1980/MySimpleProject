from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from brain_git_platform import service
from brain_git_platform.pull_requests import create_pull_request, merge_pull_request


class PullRequestMergeTests(unittest.TestCase):
    def test_create_and_merge_fast_forward_pr(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "brain"
            old_root, old_db = service.ROOT, service.DB
            service.ROOT, service.DB = root, root / "brain-git.db"
            try:
                bare = service.create_repository(service.Repository("brain", "demo"))
                work = Path(d) / "work"
                subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "brain@test.local"], cwd=work, check=True)
                subprocess.run(["git", "config", "user.name", "Brain Test"], cwd=work, check=True)
                (work / "README").write_text("initial\n", encoding="utf-8")
                subprocess.run(["git", "add", "README"], cwd=work, check=True)
                subprocess.run(["git", "commit", "-m", "initial"], cwd=work, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work, check=True, capture_output=True)

                subprocess.run(["git", "checkout", "-b", "feature"], cwd=work, check=True, capture_output=True)
                (work / "feature.txt").write_text("feature\n", encoding="utf-8")
                subprocess.run(["git", "add", "feature.txt"], cwd=work, check=True)
                subprocess.run(["git", "commit", "-m", "feature"], cwd=work, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", "feature"], cwd=work, check=True, capture_output=True)

                pr = create_pull_request("brain", "demo", "feature", "main", "Merge feature")
                merged = merge_pull_request(pr.id)
                self.assertEqual(merged.status, "merged")
                self.assertTrue(merged.merged_sha)
                head = subprocess.run(["git", "ls-remote", str(bare), "refs/heads/main"], text=True, capture_output=True, check=True).stdout.split()[0]
                self.assertEqual(head, merged.merged_sha)
            finally:
                service.ROOT, service.DB = old_root, old_db


if __name__ == "__main__":
    unittest.main()
