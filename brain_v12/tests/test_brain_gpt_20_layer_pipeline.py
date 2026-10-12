import unittest

from brain_v12.brain.brain_gpt_20_layer_pipeline import (
    LAYERS,
    BrainGPT20LayerPipeline,
)


class BrainGPT20LayerPipelineTests(unittest.TestCase):
    def test_declares_exactly_twenty_unique_ordered_layers(self):
        self.assertEqual(len(LAYERS), 20)
        self.assertEqual([layer.number for layer in LAYERS], list(range(1, 21)))
        self.assertEqual(len({layer.key for layer in LAYERS}), 20)

    def test_unconfigured_pipeline_fails_closed_and_names_missing_layers(self):
        pipeline = BrainGPT20LayerPipeline()
        status = pipeline.status()
        result = pipeline.run({"message": "hello"})
        self.assertFalse(status["ready"])
        self.assertEqual(status["status"], "NOT_CONFIGURED")
        self.assertEqual(result["status"], "PIPELINE_NOT_CONFIGURED")
        self.assertEqual(len(result["missing_required_layers"]), 20)
        self.assertEqual(result["outcomes"], [])

    def test_runs_all_registered_layers_in_order_and_returns_evidence(self):
        calls = []
        handlers = {
            layer.key: (lambda state, key=layer.key: (calls.append(key) or {"ok": True, "layer": key}))
            for layer in LAYERS
        }
        pipeline = BrainGPT20LayerPipeline(handlers)
        result = pipeline.run({"message": "hello"})
        self.assertTrue(pipeline.status()["ready"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(calls, [layer.key for layer in LAYERS])
        self.assertEqual(result["evidence"]["completed_layers"], 20)

    def test_stops_when_a_layer_reports_failure(self):
        handlers = {layer.key: (lambda state: {"ok": True}) for layer in LAYERS}
        handlers["permission_gate"] = lambda state: {"ok": False, "error": "APPROVAL_REQUIRED"}
        result = BrainGPT20LayerPipeline(handlers).run({"message": "run protected action"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "LAYER_FAILED")
        self.assertEqual(result["failed_layer"], "permission_gate")
        self.assertEqual(len(result["outcomes"]), 13)

    def test_rejects_unknown_layer_and_non_callable_handler(self):
        pipeline = BrainGPT20LayerPipeline()
        with self.assertRaises(ValueError):
            pipeline.register("imaginary_layer", lambda state: {})
        with self.assertRaises(TypeError):
            pipeline.register("input_gateway", "not callable")

    def test_invalid_request_is_rejected(self):
        pipeline = BrainGPT20LayerPipeline()
        self.assertEqual(pipeline.run("not a dict")["status"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
