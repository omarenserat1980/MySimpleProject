import unittest
from types import SimpleNamespace

from brain_v12.brain.brain_gpt_20_layer_trace import build_request_layer_trace


class BrainGPT20LayerTraceTests(unittest.TestCase):
    def test_trace_reports_exactly_twenty_layers_without_claiming_unwired_layers(self):
        brain = SimpleNamespace(memory_store=object())
        response = SimpleNamespace(ok=True, mode="model", error=None, evidence=[
            {"type": "provider", "model": "fake"},
            {"type": "model_routing", "selected_model": "fake"},
        ])
        trace = build_request_layer_trace(brain, "hello", "", response)
        self.assertEqual(trace["architecture_layers"], 20)
        self.assertEqual(len(trace["layers"]), 20)
        self.assertEqual(trace["layers"][0]["status"], "COMPLETED")
        self.assertEqual(trace["layers"][1]["status"], "NOT_WIRED")
        self.assertEqual(trace["layers"][-2]["status"], "NOT_WIRED")
        self.assertFalse(trace["execution_performed_by_trace"])

    def test_session_markers_and_tool_evidence_are_reflected(self):
        brain = SimpleNamespace(memory_store=None)
        response = SimpleNamespace(ok=False, mode="approval", error="WAITING_APPROVAL", evidence=[
            {"type": "provider"},
            {"type": "tool", "verified": False},
        ])
        trace = build_request_layer_trace(
            brain, "deploy", "[BRAIN_SESSION_MEMORY]\nknown facts\n[BRAIN_SESSION_CONTEXT]\n[user] deploy", response
        )
        by_key = {layer["key"]: layer for layer in trace["layers"]}
        self.assertEqual(by_key["conversation_manager"]["status"], "COMPLETED")
        self.assertEqual(by_key["permission_gate"]["status"], "COMPLETED")
        self.assertEqual(by_key["execution_dispatcher"]["status"], "BLOCKED")
        self.assertEqual(by_key["verification_gate"]["status"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
