import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
UI = ROOT / "web" / "brain-avatar" / "index.html"


class BrainAvatarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APP.read_text(encoding="utf-8")
        cls.html = UI.read_text(encoding="utf-8")

    def test_live_state_endpoint_uses_read_only_liveness_assessment(self):
        self.assertIn('@app.get("/api/brain-avatar/state")', self.app)
        start = self.app.index('def brain_avatar_state():')
        end = self.app.find('\n@app.', start + 1)
        if end < 0:
            end = len(self.app)
        route = self.app[start:end]
        self.assertIn('assess_brain_liveness(store=store, device_bridge=device_bridge, cognitive=cognitive)', route)
        self.assertNotIn('run_execution_probe', route)
        self.assertIn('"source": "live_brain_liveness_assessment"', route)

    def test_ui_polls_real_endpoint_and_does_not_claim_connection_on_failure(self):
        self.assertIn("fetch('/api/brain-avatar/state'", self.html)
        self.assertIn("window.setInterval(pollLiveState,5000)", self.html)
        self.assertIn("Brain: غير متصل — عرض الحالة اليدوية", self.html)
        self.assertIn('id="liveMode"', self.html)

    def test_avatar_has_accessible_arabic_mobile_and_reduced_motion_support(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('@media(max-width:720px)', self.html)
        self.assertIn('prefers-reduced-motion:reduce', self.html)
        self.assertIn('aria-live="polite"', self.html)

    def test_all_supported_visual_states_exist(self):
        for state in ("IDLE", "LISTENING", "THINKING", "SPEAKING", "SUCCESS", "UNCERTAIN", "ERROR"):
            self.assertIn(state, self.html)

    def test_no_camera_microphone_or_external_service_integration(self):
        for forbidden in ("getUserMedia", "MediaRecorder", "face-api", "navigator.mediaDevices"):
            self.assertNotIn(forbidden, self.html)
        self.assertNotIn("https://", self.html)
        self.assertNotIn("http://", self.html)


if __name__ == "__main__":
    unittest.main()
