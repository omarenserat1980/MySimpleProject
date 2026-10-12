import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.self_healing import tool_evolution


class ToolEvolutionTests(unittest.TestCase):
    def test_records_redacted_shape_and_proposal(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tool_evolution, "_state_dir", return_value=Path(tmp)):
            result = tool_evolution.record_invocation("github.write", "FAILED", {"password": "never-store-me", "repository": "private-repo"}, duration_ms=12, error="HTTP_403", risk="high", permission="github.write")
            self.assertTrue(result["recorded"])
            event = json.loads((Path(tmp) / "invocations.jsonl").read_text().splitlines()[0])
            encoded = json.dumps(event)
            self.assertNotIn("never-store-me", encoded)
            self.assertNotIn("private-repo", encoded)
            self.assertEqual(event["params_shape"]["password"], "[REDACTED_FIELD]")
            proposal = json.loads((Path(tmp) / "improvement_proposals.json").read_text())
            self.assertEqual(proposal["tools"]["github.write"]["last_status"], "FAILED")
            self.assertFalse(proposal["safety"]["source_code_modified"])

    def test_repeat_failure_proposes_no_retry_loop(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tool_evolution, "_state_dir", return_value=Path(tmp)):
            for _ in range(3):
                tool_evolution.record_invocation("cloud.boot", "FAILED", error="BOOT_ERROR")
            proposal = json.loads((Path(tmp) / "improvement_proposals.json").read_text())
            kinds = {item["kind"] for item in proposal["tools"]["cloud.boot"]["improvements"]}
            self.assertIn("repeat_failure", kinds)

    def test_observed_adapter_records_exception_and_reraises(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(tool_evolution, "_state_dir", return_value=Path(tmp)):
            def fail(_):
                raise RuntimeError("failure")
            with self.assertRaises(RuntimeError):
                tool_evolution.invoke_observed("sample", fail)
            events = (Path(tmp) / "invocations.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(events[0])["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
