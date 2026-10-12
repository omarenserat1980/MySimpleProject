import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.tool_foundry import ProposalError, scaffold, validate_proposal


BASE = {
    "name": "example_tool",
    "purpose": "Demonstrate safe tool proposal scaffolding.",
    "inputs": [{"name": "item_id", "type": "string", "required": True}],
    "outputs": [{"name": "status", "type": "string"}],
    "permissions": ["read"],
}


class ToolFoundryTests(unittest.TestCase):
    def test_normalizes_and_keeps_execution_disabled(self):
        result = validate_proposal(BASE)
        self.assertEqual(result["schema_version"], 1)
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["production_registration"], "REVIEW_REQUIRED")

    def test_marks_privileged_permissions_for_review(self):
        proposal = {**BASE, "permissions": ["write", "secrets"]}
        result = validate_proposal(proposal)
        self.assertTrue(result["requires_human_review"])

    def test_rejects_path_traversal(self):
        with self.assertRaises(ProposalError):
            validate_proposal({**BASE, "name": "../bad"})

    def test_rejects_unknown_permission(self):
        with self.assertRaises(ProposalError):
            validate_proposal({**BASE, "permissions": ["root_access"]})

    def test_scaffold_creates_inert_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = scaffold(BASE, tmp)
            self.assertTrue((target / "tool.json").is_file())
            self.assertTrue((target / "README.md").is_file())
            source = (target / "tool.py").read_text(encoding="utf-8")
            self.assertIn("TOOL_ENABLED = False", source)
            self.assertIn("TOOL_NOT_IMPLEMENTED_OR_APPROVED", source)
            manifest = json.loads((target / "tool.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["execution_enabled"])

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            scaffold(BASE, tmp)
            with self.assertRaises(ProposalError):
                scaffold(BASE, tmp)


if __name__ == "__main__":
    unittest.main()
