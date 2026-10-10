import unittest
from types import SimpleNamespace

from brain_v12.brain.brain_gpt_20_layer_runtime import build_layer_runtime_status


class BrainGPT20LayerRuntimeTests(unittest.TestCase):
    def test_reports_all_twenty_layers_and_does_not_claim_ready_for_gaps(self):
        brain_ai = SimpleNamespace(
            model_router=None,
            provider=object(),
            tools={},
            memory_store=None,
            cognitive=None,
            _tool_intents=lambda result: [],
            chat=lambda *args, **kwargs: None,
            execute_tool=lambda *args, **kwargs: {},
            _verify_tool_outcome=lambda result: False,
            _diagnose_and_repair=lambda *args, **kwargs: None,
        )
        status = build_layer_runtime_status(brain_ai)
        self.assertEqual(status["architecture_layers"], 20)
        self.assertEqual(len(status["layers"]), 20)
        self.assertEqual([x["number"] for x in status["layers"]], list(range(1, 21)))
        self.assertEqual(status["status"], "INTEGRATION_INCOMPLETE")
        self.assertFalse(status["ready"])
        self.assertFalse(status["execution_performed"])
        self.assertGreater(status["not_wired_layers"], 0)

    def test_session_store_enables_session_context_and_memory_adapters(self):
        brain_ai = SimpleNamespace(
            model_router=SimpleNamespace(select=lambda task="chat": {"ok": True}),
            provider=object(),
            tools={},
            memory_store=None,
            cognitive=object(),
            _tool_intents=lambda result: [],
            chat=lambda *args, **kwargs: None,
            execute_tool=lambda *args, **kwargs: {},
            _verify_tool_outcome=lambda result: False,
            _diagnose_and_repair=lambda *args, **kwargs: None,
        )
        session_store = SimpleNamespace(
            get=lambda sid: {},
            context_messages=lambda sid, limit=24: [],
            get_memory=lambda sid: {},
            set_memory=lambda sid, summary: {},
        )
        status = build_layer_runtime_status(brain_ai, session_store)
        by_key = {item["key"]: item for item in status["layers"]}
        for key in ("conversation_manager", "context_builder", "memory_retrieval", "memory_consolidation"):
            self.assertEqual(by_key[key]["status"], "READY" if key != "memory_consolidation" else "PARTIAL")
        self.assertFalse(status["ready"])


if __name__ == "__main__":
    unittest.main()
