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

    def test_unissued_proposal_is_rejected(self):
        executor = BrainSuggestionExecutor(tool_registry={"status": lambda **kw: {"ready": True}}, dry_run=False)
        result = executor.execute({"proposal_id": "forged", "title": "Status", "rationale": "Check",
                                   "tool_name": "status", "arguments": {}, "risk": "low",
                                   "requires_approval": False})
        self.assertEqual(result["status"], "PROPOSAL_NOT_ISSUED")

    def test_risk_downgrade_tampering_is_rejected(self):
        calls = []
        executor = BrainSuggestionExecutor(tool_registry={"repair": lambda **kw: calls.append(kw)}, dry_run=False)
        proposal = executor.propose(title="Repair", rationale="Fix", tool_name="repair",
                                     arguments={}, risk="high")["proposal"]
        altered = dict(proposal)
        altered["risk"] = "low"
        result = executor.execute(altered)
        self.assertEqual(result["status"], "PROPOSAL_TAMPERED")
        self.assertEqual(calls, [])

    def test_invalid_risk_is_rejected_at_proposal_time(self):
        executor = BrainSuggestionExecutor(tool_registry={"safe": lambda **kw: True})
        result = executor.propose(title="Test", rationale="Check", tool_name="safe",
                                  arguments={}, risk="unrestricted")
        self.assertEqual(result["status"], "INVALID_RISK")

    def test_registered_tool_runs_when_enabled(self):
        calls = []
        executor = BrainSuggestionExecutor(tool_registry={"status": lambda **kw: calls.append(kw) or {"ready": True}}, dry_run=False)
        proposal = executor.propose(title="Status", rationale="Read only", tool_name="status",
                                     arguments={"node": "arkan-virtual-01"})["proposal"]
        result = executor.execute(proposal)
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(calls, [{"node": "arkan-virtual-01"}])

    def test_high_risk_requires_approval(self):
        executor = BrainSuggestionExecutor(tool_registry={"repair": lambda **kw: True}, dry_run=False)
        proposal = executor.propose(title="Repair", rationale="Fix", tool_name="repair",
                                    arguments={}, risk="high")["proposal"]
        self.assertEqual(executor.execute(proposal)["status"], "APPROVAL_REQUIRED")

    def test_mutation_gate_and_evidence(self):
        executor = BrainSuggestionExecutor(tool_registry={"repair": lambda **kw: {"changed": True}}, dry_run=False)
        proposal = executor.propose(title="Repair", rationale="Fix", tool_name="repair",
                                    arguments={}, risk="medium")["proposal"]
        self.assertEqual(executor.execute(proposal)["status"], "MUTATION_GATE_BLOCKED")
        result = executor.execute(proposal, allow_mutation=True)
        self.assertEqual(executor.verify(result, {})["status"], "EVIDENCE_REQUIRED")
        self.assertEqual(executor.verify(result, {"verified": True, "source": "test"})["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
