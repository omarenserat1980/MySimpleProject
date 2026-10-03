import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "brain-autopilot"

class BrainAutopilotPluginTests(unittest.TestCase):
    def test_manifest_and_skill_layout(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "brain-autopilot")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["skills"], "./skills/")
        skills = sorted(p for p in (PLUGIN / "skills").iterdir() if p.is_dir())
        self.assertGreaterEqual(len(skills), 3)
        for skill in skills:
            doc = skill / "SKILL.md"
            self.assertTrue(doc.is_file())
            text = doc.read_text(encoding="utf-8")
            self.assertRegex(text, r"^---\nname: [^\n]+\ndescription: [^\n]+\n---\n")
            self.assertNotIn("..", doc.as_posix())

    def test_no_runtime_secrets_or_mcp_dependency_declared(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn(".mcp.json", manifest.get("skills", ""))

if __name__ == "__main__":
    unittest.main()
