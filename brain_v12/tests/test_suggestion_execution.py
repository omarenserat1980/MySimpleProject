import unittest
from brain_v12.brain.suggestion_execution import BrainSuggestionExecutor


class SuggestionExecutionTests(unittest.TestCase):
    def test_unknown_tool_is_rejected(self):
        executor = BrainSuggestionExecutor(tool_registry={"safe": lambda **kw: kw})
        result = executor.propose(title="Test", rationale="Check", tool_name="shell", arguments={})
        self.assertEqual(result["status"], "TOOL_NOT_REGISTERED")

    def test_dry_run_is_default(self):
        calls = []
        executor = BrainSuggestionExecutor(tool_registry={"safe": lambda **kw: calls.append(kw)})
        proposal = executor.propose(title="Check", rationale="Read only", tool_name="safe", arguments={})
        result = executor.execute(proposal["proposal"])
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertEqual(calls, [])

    def test_registered_tool_runs_when_enabled(self):
        calls = []
        executor = BrainSuggestionExecutor(tool_registry={"status": lambda **kw: calls.append(kw) or {"ready": True}}, dry_run=False)
        proposal = executor.propose(title="Status", rationale="Read only", tool_name="status", arguments={"node": "arkan-virtual-01"})
        result = executor.execute(proposal["proposal"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(calls, [{"node": "arkan-virtual-01"}])

    def test_high_risk_requires_approval(self):
        executor = BrainSuggestionExecutor(tool_registry={"repair": lambda **kw: True}, dry_run=False)
        proposal = executor.propose(title="Repair", rationale="Fix", tool_name="repair", arguments={}, risk="high")
        self.assertEqual(executor.execute(proposal["proposal"])["status"], "APPROVAL_REQUIRED")

    def test_mutation_gate_and_evidence(self):
        executor = BrainSuggestionExecutor(tool_registry={"repair": lambda **kw: {"changed": True}}, dry_run=False)
        proposal = executor.propose(title="Repair", rationale="Fix", tool_name="repair", arguments={}, risk="medium")
        self.assertEqual(executor.execute(proposal["proposal"])["status"], "MUTATION_GATE_BLOCKED")
        result = executor.execute(proposal["proposal"], allow_mutation=True)
        self.assertEqual(executor.verify(result, {})["status"], "EVIDENCE_REQUIRED")
        self.assertEqual(executor.verify(result, {"verified": True, "source": "test"})["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
