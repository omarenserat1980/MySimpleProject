import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "brain-autopilot"
SKILLS = PLUGIN / "skills"

class BrainAutopilotPluginTests(unittest.TestCase):
    def test_manifest_and_skill_layout(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "brain-autopilot")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["skills"], "./skills/")
        skills = sorted(p for p in SKILLS.iterdir() if p.is_dir())
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

    def test_skill_roles_and_evidence_contract(self):
        docs = {
            p.name: (p / "SKILL.md").read_text(encoding="utf-8")
            for p in SKILLS.iterdir() if p.is_dir()
        }
        required = {
            "brain-github-orchestrator": ["Decision loop", "Core rule", "evidence"],
            "github-change-verify": ["Required loop", "Evidence gate", "Never claim VERIFIED_COMPLETED"],
            "github-failure-repair": ["Workflow", "first actionable failure", "Do not weaken tests"],
            "github-repo-audit": ["Workflow", "verified working behavior", "Mutation boundary"],
        }
        for skill, markers in required.items():
            self.assertIn(skill, docs)
            for marker in markers:
                self.assertIn(marker, docs[skill])

    def test_orchestrator_routes_to_specialized_skills(self):
        text = (SKILLS / "brain-github-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("github-repo-audit", text)
        self.assertIn("github-failure-repair", text)
        self.assertIn("github-change-verify", text)

    def test_no_false_success_language(self):
        docs = "\n".join(
            (p / "SKILL.md").read_text(encoding="utf-8")
            for p in SKILLS.iterdir() if p.is_dir()
        )
        self.assertIn("do not skip evidence gates", docs.lower())
        self.assertIn("do not", docs.lower())
        self.assertIn("unverified", docs.lower())

if __name__ == "__main__":
    unittest.main()
