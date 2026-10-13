"""Focused offline tests for Brain integration diagnostics."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).with_name("brain_integration_diagnostics.py")
SPEC = importlib.util.spec_from_file_location("brain_integration_diagnostics", SCRIPT)
diag = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(diag)


class DiagnosticsTests(unittest.TestCase):
    def test_local_xor_is_software_only(self):
        report = diag.local_asic_check()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["cases"], 4)
        self.assertFalse(report["real_hardware_measurement"])

    def _fake_server(self, tool_error=False):
        def fake(url, method="GET", body=None, headers=None, timeout=10.0):
            if method == "GET":
                return 405, {"message": "GET not supported"}
            rpc_method = body.get("method") if body else None
            if rpc_method == "initialize":
                return 200, {"jsonrpc": "2.0", "id": body["id"], "result": {}}
            if rpc_method == "notifications/initialized":
                return 202, None
            if rpc_method == "tools/list":
                return 200, {"jsonrpc": "2.0", "id": body["id"],
                             "result": {"tools": [{"name": "brain.status"}]}}
            if rpc_method == "tools/call":
                result = {"content": [{"type": "text", "text": "ok"}]}
                if tool_error:
                    result["isError"] = True
                return 200, {"jsonrpc": "2.0", "id": body["id"], "result": result}
            if url.endswith("/.well-known/oauth-protected-resource/mcp"):
                return 404, {}
            return 404, {}
        return fake

    def test_mcp_handshake_and_tool_call(self):
        with patch.object(diag, "http_json", side_effect=self._fake_server()) as mocked:
            report = diag.live_mcp_check("https://example.invalid", timeout=3)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["endpoint_probe"]["http_status"], 405)
        steps = [c["step"] for c in report["checks"]]
        self.assertEqual(steps, ["initialize", "notifications/initialized",
                                 "tools/list", "tools/call brain.status"])
        self.assertTrue(all(call.kwargs.get("timeout") == 3 or
                            (len(call.args) > 4 and call.args[4] == 3)
                            for call in mocked.call_args_list))

    def test_tool_level_error_is_not_pass(self):
        with patch.object(diag, "http_json", side_effect=self._fake_server(tool_error=True)):
            report = diag.live_mcp_check("https://example.invalid")
        self.assertEqual(report["status"], "FAIL", report)
        self.assertFalse(next(c for c in report["checks"]
                              if c["step"] == "tools/call brain.status")["pass"])

    def test_nonpositive_timeout_rejected(self):
        with self.assertRaises(ValueError):
            diag.live_mcp_check("https://example.invalid", timeout=0)


if __name__ == "__main__":
    unittest.main()
