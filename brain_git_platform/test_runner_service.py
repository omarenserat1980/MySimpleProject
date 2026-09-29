from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brain_git_platform import service
from brain_git_platform.runner.service import execute_run
from brain_git_platform.workflows import dispatch


class RunnerServiceTests(unittest.TestCase):
    def test_execute_updates_run_and_writes_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "brain"
            old_root, old_db = service.ROOT, service.DB
            service.ROOT, service.DB = root, root / "brain-git.db"
            try:
                service.create_repository(service.Repository("brain", "demo"))
                run = dispatch("brain", "demo", "test", "main")
                manifest = root / "workflow.json"
                manifest.parent.mkdir(parents=True, exist_ok=True)
                manifest.write_text(json.dumps({
                    "name": "test",
                    "steps": [{"name": "ok", "command": ["python", "-c", "print('runner-ok')"]}]
                }), encoding="utf-8")
                result = execute_run(run.id, manifest, root / "workspace")
                self.assertEqual(result["status"], "success")
                artifact = root / "artifacts" / str(run.id) / "workflow-result.txt"
                self.assertTrue(artifact.exists())
                self.assertIn("runner-ok", artifact.read_text(encoding="utf-8"))
            finally:
                service.ROOT, service.DB = old_root, old_db


if __name__ == "__main__":
    unittest.main()
