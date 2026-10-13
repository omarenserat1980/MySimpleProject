import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from brain_v12.brain import universal_simulator_api as api


class FakeProvider:
    configured = True

    def status(self):
        return {"provider": "openai", "configured": True}

    def respond(self, user_text, context="", instructions=""):
        return {
            "ok": True,
            "provider": "openai",
            "model": "test-model",
            "response_id": "resp_test",
            "reply": '{"root_cause_hypotheses":["test hypothesis"],"evidence":["mock evidence"],"confidence":0.8,"recommended_actions":["run a focused test"],"required_tools":[],"proposed_files":[],"proposed_scripts":[],"test_plan":["unit test"],"rollback_plan":["revert patch"],"risk_level":"low","requires_human_approval":false}',
        }


class UniversalSimulatorApiTests(unittest.TestCase):
    def test_redacts_secrets_from_values_and_keys(self):
        value = api._redact({
            "api_key": "secret-value",
            "log": "Authorization: abc123 Bearer xyz987 token=token-value; Authorization: Bearer authsecret",
        })
        rendered = json.dumps(value)
        self.assertNotIn("secret-value", rendered)
        self.assertNotIn("abc123", rendered)
        self.assertNotIn("authsecret", rendered)
        self.assertNotIn("xyz987", rendered)
        self.assertNotIn("token-value", rendered)

    def test_catalog_reports_discovery_not_connectivity(self):
        items = api.discover_simulators()
        self.assertGreaterEqual(len(items), 5)
        termux = next(item for item in items if item["simulator_id"] == "termux-brain")
        self.assertIn(termux["discovery_status"], {"DISCOVERED", "NOT_FOUND"})
        self.assertEqual(termux["connection_status"], "NOT_CONFIGURED")
        self.assertIn("Repository evidence is not proof", "Repository evidence is not proof of external connectivity or live execution.")

    def test_powershell_catalog_points_to_sandboxed_emulator(self):
        entry = api._SIMULATOR_CATALOG["powershell-brain"]
        expected = {
            "brain_v12/brain/powershell_emulator.py",
            "brain_v12/tests/test_powershell_emulator.py",
        }
        self.assertEqual(set(entry["evidence_paths"]), expected)
        for relative_path in entry["evidence_paths"]:
            self.assertTrue((api._ROOT / relative_path).is_file(), relative_path)

    def test_register_custom_simulator_does_not_claim_connection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_SIMULATOR_REGISTRY_PATH": str(Path(tmp) / "registry.json")
        }):
            result = api.register_simulator({
                "simulator_id": "render-test-adapter",
                "name": "Render test adapter",
                "execution_mode": "EXTERNAL",
                "capabilities": ["health_check"],
            })
            self.assertTrue(result["ok"])
            self.assertEqual(result["simulator"]["connection_status"], "NOT_PROBED")
            persisted = json.loads((Path(tmp) / "registry.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["render-test-adapter"]["execution_mode"], "EXTERNAL")

    def test_analysis_returns_not_configured_without_provider_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_REPAIR_AUDIT_PATH": str(Path(tmp) / "audit.jsonl")
        }), patch.object(api, "_PROVIDER", FakeProvider()) as provider:
            provider.configured = False
            result = api.analyze_error({"simulator_id": "azure-brain", "message": "deployment timeout"})
            self.assertEqual(result["status"], "NOT_CONFIGURED")
            self.assertFalse(result["repair_executed"])

    def test_analysis_uses_provider_and_never_claims_repair_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BRAIN_REPAIR_AUDIT_PATH": str(Path(tmp) / "audit.jsonl")
        }), patch.object(api, "_PROVIDER", FakeProvider()):
            result = api.analyze_error({
                "simulator_id": "render-brain",
                "error_type": "DeploymentTimeout",
                "message": "deployment timeout",
                "context": {"api_key": "must-not-leak"},
            })
            self.assertEqual(result["status"], "AI_ANALYSIS_COMPLETED")
            self.assertFalse(result["repair_executed"])
            self.assertNotIn("must-not-leak", json.dumps(result))
            audit = (Path(tmp) / "audit.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(audit), 1)
            self.assertEqual(json.loads(audit[0])["status"], "AI_ANALYSIS_COMPLETED")

    def test_invalid_structured_analysis_is_rejected(self):
        self.assertIsNone(api._parse_analysis("not-json"))

    def test_invalid_simulator_id_rejected(self):
        with self.assertRaises(HTTPException):
            api.register_simulator({"simulator_id": "../unsafe", "name": "Unsafe"})


if __name__ == "__main__":
    unittest.main()
