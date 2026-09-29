from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brain_git_platform.workflow_manifest import load


class WorkflowManifestTests(unittest.TestCase):
    def test_load_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "workflow.json"
            path.write_text(json.dumps({
                "name": "test",
                "steps": [{"name": "unit", "command": ["python", "-V"]}]
            }), encoding="utf-8")
            workflow = load(path)
            self.assertEqual(workflow.name, "test")
            self.assertEqual(workflow.steps[0].command, ("python", "-V"))


if __name__ == "__main__":
    unittest.main()
