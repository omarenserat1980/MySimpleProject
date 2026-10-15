import unittest

from brain_v12.tool_lifecycle import ToolState, build_and_verify_tool


class ToolLifecycleTests(unittest.TestCase):
    def test_passing_simulation_immediately_builds_and_verifies_real_tool(self):
        calls = []
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: calls.append("simulate") or True,
            build_real=lambda: calls.append("build_real") or object(),
            verify_real=lambda impl: calls.append("verify_real") or {
                "verified": True,
                "evidence_id": "test-run-001",
            },
        )
        self.assertEqual(calls, ["simulate", "build_real", "verify_real"])
        self.assertEqual(result.state, ToolState.REAL_VERIFIED)
        self.assertIn(ToolState.REAL_VERIFIED.value, result.history)
        self.assertEqual(result.evidence["evidence_id"], "test-run-001")

    def test_failed_simulation_never_builds_real_tool(self):
        calls = []
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: calls.append("simulate") or False,
            build_real=lambda: calls.append("build_real") or object(),
            verify_real=lambda impl: {"verified": True},
        )
        self.assertEqual(calls, ["simulate"])
        self.assertEqual(result.state, ToolState.BLOCKED)

    def test_missing_real_evidence_blocks_completion(self):
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: True,
            build_real=object,
            verify_real=lambda impl: {},
        )
        self.assertEqual(result.state, ToolState.BLOCKED)
        self.assertNotIn(ToolState.REAL_VERIFIED.value, result.history)

    def test_unverified_evidence_blocks_completion(self):
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: True,
            build_real=object,
            verify_real=lambda impl: {"verified": False, "reason": "offline"},
        )
        self.assertEqual(result.state, ToolState.BLOCKED)

    def test_activation_requires_authorization(self):
        calls = []
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: True,
            build_real=object,
            verify_real=lambda impl: {"verified": True, "evidence_id": "real-1"},
            activate=lambda impl: calls.append("activate") or True,
            activation_authorized=False,
        )
        self.assertEqual(result.state, ToolState.BLOCKED)
        self.assertEqual(calls, [])
        self.assertIn(ToolState.REAL_VERIFIED.value, result.history)

    def test_authorized_activation_requires_success(self):
        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: True,
            build_real=object,
            verify_real=lambda impl: {"verified": True, "evidence_id": "real-1"},
            activate=lambda impl: True,
            activation_authorized=True,
        )
        self.assertEqual(result.state, ToolState.ACTIVE)

    def test_builder_exception_is_recorded_as_failure(self):
        def fail_build():
            raise RuntimeError("adapter unavailable")

        result = build_and_verify_tool(
            tool_name="example",
            simulate=lambda: True,
            build_real=fail_build,
            verify_real=lambda impl: {"verified": True},
        )
        self.assertEqual(result.state, ToolState.FAILED)
        self.assertIn("adapter unavailable", result.reason)


if __name__ == "__main__":
    unittest.main()
