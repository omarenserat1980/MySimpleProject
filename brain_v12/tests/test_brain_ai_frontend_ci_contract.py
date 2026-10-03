import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/brain-ai-frontend.yml")

class BrainAIFrontendCIContractTest(unittest.TestCase):
    def test_workflow_has_manual_and_push_triggers(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("push:", text)
        self.assertIn('branches: [main]', text)

    def test_workflow_covers_backend_contract_changes(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for path in (
            "brain_v12/brain/brain_ai_api.py",
            "brain_v12/brain/chat_session_api.py",
            "brain_v12/tests/test_brain_ai_api.py",
            "brain_v12/tests/test_chat_session_api.py",
        ):
            self.assertIn(path, text)

    def test_workflow_has_verification_gates(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "test_brain_ai_frontend",
            "test_chat_session_api",
            "test_brain_ai_api",
            "compileall",
            "node --check",
            "encodeURIComponent(sid)",
            "evidenceView",
        ):
            self.assertIn(marker, text)

if __name__ == "__main__":
    unittest.main()
