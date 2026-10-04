import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HTML = Path("brain_v12/web/brain-chat/index.html")

class BrainAIFrontendTest(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")

    def test_frontend_contract(self):
        required = [
            'Brain AI',
            '/api/brain-ai/status',
            'localStorage',
            'brain_ai_chats_v2',
            'brain_ai_api_base',
            'window.BRAIN_API_BASE',
            './config.js',
            '/api/brain-chat/sessions',
            'ensureSession',
            '/messages',
            '/sync?after=',
            'syncSession',
            'startSync',
            'syncCursor',
            'sessionId',
            'openSettings',
            'renderHistory',
            'snapshot',
            'evidenceView',
            'سجل التنفيذ والتحقق',
            '/api/brain/cloud/status',
            'async function status()',
            'cloudStatus()',
        ]
        for item in required:
            self.assertIn(item, self.html, item)

    def test_no_legacy_chat_session_endpoint(self):
        self.assertIn('encodeURIComponent(sid)', self.html)
        self.assertIn('/messages', self.html)

    def test_javascript_syntax(self):
        scripts = re.findall(r'<script(?:[^>]*)>(.*?)</script>', self.html, re.S | re.I)
        self.assertTrue(scripts)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write("\n".join(scripts))
            path = f.name
        try:
            result = subprocess.run(["node", "--check", path], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            Path(path).unlink(missing_ok=True)


    def test_supervisor_evidence_labels_objective_as_unverified(self):
        for item in ("supervisor_execution", "objective_verified", "الهدف غير مثبت"):
            self.assertIn(item, self.html)

    def test_pages_workflow_is_main_only_and_deploys_an_artifact(self):
        workflow = Path(".github/workflows/brain-pages.yml").read_text(encoding="utf-8")
        for item in ("branches: [main]", "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4", "BRAIN_API_ORIGIN"):
            self.assertIn(item, workflow)

if __name__ == "__main__":
    unittest.main()
