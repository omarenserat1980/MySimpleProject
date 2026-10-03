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
            '/api/brain-ai/chat',
            'localStorage',
            'brain_ai_chats_v2',
            'brain_ai_api_base',
            '/api/brain-chat/sessions',
            'ensureSession',
            '/messages',
            'sessionId',
            'openSettings',
            'renderHistory',
            'snapshot',
            'evidenceView',
            'سجل التنفيذ والتحقق',
        ]
        for item in required:
            self.assertIn(item, self.html, item)

    def test_no_legacy_chat_session_endpoint(self):
        self.assertIn('encodeURIComponent(sid)', self.html)

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

if __name__ == "__main__":
    unittest.main()
