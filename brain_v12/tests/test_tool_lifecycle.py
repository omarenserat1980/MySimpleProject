import unittest

from brain_v12.tool_lifecycle import ToolState, build_and_verify_tool


class ToolLifecycleTests(unittest.TestCase):
    def test_simulation_pass_immediately_builds_and_verifies_real_adapter(self):
        calls = []
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: calls.append("simulate") or True,
            build_real=lambda: calls.append("build_real") or object(),
            verify_real=lambda impl: calls.append("verify_real") or {
                "verified": True, "evidence_id": "integration-test-001"
            },
        )
        self.assertEqual(calls, ["simulate", "build_real", "verify_real"])
        self.assertEqual(result.state, ToolState.REAL_VERIFIED)

    def test_simulation_failure_prevents_real_build(self):
        calls = []
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: calls.append("simulate") or False,
            build_real=lambda: calls.append("build_real") or object(),
            verify_real=lambda impl: {"verified": True},
        )
        self.assertEqual(calls, ["simulate"])
        self.assertEqual(result.state, ToolState.BLOCKED)

    def test_missing_or_negative_evidence_blocks_verification(self):
        for evidence in ({}, {"verified": False, "reason": "offline"}):
            with self.subTest(evidence=evidence):
                result = build_and_verify_tool(
                    tool_name="example", simulate=lambda: True,
                    build_real=object, verify_real=lambda impl: evidence,
                )
                self.assertEqual(result.state, ToolState.BLOCKED)

    def test_activation_requires_authorization_and_success(self):
        calls = []
        kwargs = dict(
            tool_name="example", simulate=lambda: True, build_real=object,
            verify_real=lambda impl: {"verified": True, "evidence_id": "real-1"},
            activate=lambda impl: calls.append("activate") or True,
        )
        blocked = build_and_verify_tool(**kwargs, activation_authorized=False)
        self.assertEqual(blocked.state, ToolState.BLOCKED)
        self.assertEqual(calls, [])
        active = build_and_verify_tool(**kwargs, activation_authorized=True)
        self.assertEqual(active.state, ToolState.ACTIVE)
        self.assertEqual(calls, ["activate"])

    def test_builder_failure_is_recorded(self):
        def fail():
            raise RuntimeError("adapter unavailable")
        result = build_and_verify_tool(
            tool_name="example", simulate=lambda: True, build_real=fail,
            verify_real=lambda impl: {"verified": True},
        )
        self.assertEqual(result.state, ToolState.FAILED)
        self.assertIn("adapter unavailable", result.reason)


if __name__ == "__main__":
    unittest.main()
