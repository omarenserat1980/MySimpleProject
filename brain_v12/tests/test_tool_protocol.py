import unittest

from brain_v12.brain.tool_protocol import parse_tool_call


class ToolProtocolTests(unittest.TestCase):
    def test_parses_strict_tool_call(self):
        call = parse_tool_call(
            '{"type":"tool_call","call_id":"c1","name":"echo","arguments":{"x":1}}'
        )
        self.assertEqual(call.call_id, "c1")
        self.assertEqual(call.name, "echo")
        self.assertEqual(call.arguments, {"x": 1})

    def test_rejects_invalid_payload(self):
        self.assertIsNone(parse_tool_call("not-json"))
        self.assertIsNone(parse_tool_call({"type": "final", "reply": "done"}))
        self.assertIsNone(
            parse_tool_call({"type": "tool_call", "call_id": "c1",
                             "name": "echo", "arguments": []})
        )


if __name__ == "__main__":
    unittest.main()
