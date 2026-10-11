import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "web" / "brain-chat-simulator.html"
CHAT_API = ROOT / "brain" / "chat_session_api.py"
APP = ROOT / "app.py"


class BrainChatSimulatorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = UI.read_text(encoding="utf-8")
        cls.chat_api = CHAT_API.read_text(encoding="utf-8")
        cls.app = APP.read_text(encoding="utf-8")

    def test_page_is_arabic_rtl_and_mobile_responsive(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn("@media(max-width:700px)", self.html)
        self.assertIn('id="messageInput"', self.html)

    def test_uses_existing_brain_chat_session_endpoints(self):
        for endpoint in ("/api/brain-chat/sessions", "/api/brain-ai/status", "/health"):
            self.assertIn(endpoint, self.html)
        self.assertIn('prefix="/api/brain-chat"', self.chat_api)
        self.assertIn('@r.post("/sessions/{session_id}/messages")', self.chat_api)
        self.assertIn('app.mount("/",StaticFiles(directory=os.path.join(ROOT,"web"),html=True),name="ui")', self.app.replace(" ", ""))

    def test_messages_use_safe_unapproved_mode(self):
        self.assertIn("approved:false", self.html)
        self.assertNotIn("approved:true", self.html.lower())
        self.assertIn("لا تشغّل أوامر نظام", self.html)

    def test_dynamic_messages_are_inserted_as_text_not_html(self):
        self.assertIn("body.textContent=escapeText(text)", self.html)
        self.assertNotIn("body.innerHTML", self.html)

    def test_live_status_is_read_from_api_not_hardcoded_as_connected(self):
        self.assertIn('api("/health")', self.html)
        self.assertIn('api("/api/brain-ai/status")', self.html)
        self.assertIn('تعذّر الاتصال', self.html)


if __name__ == "__main__":
    unittest.main()
