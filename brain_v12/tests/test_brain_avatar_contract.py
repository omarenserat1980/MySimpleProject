import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from brain_v12.brain.avatar_state import resolve_avatar_event
from brain_v12.brain.human_presence_pulse import evaluate_pulse, load_pulse, MEMORY_KEY

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
UI = ROOT / "web" / "brain-avatar" / "index.html"


class PulseMemoryStub:
    def __init__(self):
        self.values = {}

    def memories(self):
        return [{"key": key, "value": value} for key, value in self.values.items()]

    def save_memory(self, key, value):
        self.values[key] = value


class HumanPresencePulseTests(unittest.TestCase):
    def test_pulse_persists_one_bounded_tick_and_does_not_claim_render(self):
        store = PulseMemoryStub()
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        state = evaluate_pulse(store, now=now)
        self.assertEqual(state["pulse_id"], "HUMAN_PRESENCE")
        self.assertEqual(state["tick_sequence"], 1)
        self.assertEqual(state["visual_state"], "PENDING_RENDER_CONFIRMATION")
        self.assertEqual(state["last_render_status"], "API_POLLED_RENDER_NOT_INDEPENDENTLY_VERIFIED")
        self.assertIn(MEMORY_KEY, store.values)
        self.assertEqual(load_pulse(store)["tick_sequence"], 1)

    def test_pulse_tick_is_rate_limited(self):
        store = PulseMemoryStub()
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        first = evaluate_pulse(store, now=now)
        second = evaluate_pulse(store, now=now + timedelta(seconds=10))
        self.assertEqual(first["tick_sequence"], 1)
        self.assertEqual(second["tick_sequence"], 1)

    def test_invalid_persisted_state_fails_closed(self):
        store = PulseMemoryStub()
        store.values[MEMORY_KEY] = "{broken"
        state = load_pulse(store)
        self.assertFalse(state["enabled"])
        self.assertEqual(state["last_render_status"], "INVALID_PERSISTED_STATE")


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
        self.assertIn('store.events(50)', route)
        self.assertIn("resolve_avatar_event(store.events(50))", route)
        self.assertIn('if event_source != "recent_runtime_event"', route)
        self.assertLess(route.index("resolve_avatar_event(store.events(50))"), route.index('if event_source != "recent_runtime_event"'))
        self.assertIn('"source": event_source', route)
        self.assertIn('evaluate_pulse(store, display_target="brain-avatar-ui")', route)
        self.assertIn('"human_presence_pulse": pulse_status', route)

    def test_recent_supervisor_event_drives_thinking_expression(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        result = resolve_avatar_event([{
            "kind": "BRAIN_SUPERVISOR_RUN_REQUESTED",
            "payload": '{"job_id":"job-1"}',
            "created_at": (now - timedelta(seconds=5)).isoformat(),
        }], now=now)
        self.assertEqual(result["state"], "THINKING")
        self.assertEqual(result["event_type"], "BRAIN_SUPERVISOR_RUN_REQUESTED")
        self.assertEqual(result["source"], "recent_runtime_event")

    def test_chat_events_drive_thinking_speaking_and_error_states(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        started = resolve_avatar_event([{
            "kind": "BRAIN_CHAT_REQUEST_STARTED", "payload": {"trace_id": "safe-id"},
            "created_at": now.isoformat(),
        }], now=now)
        spoken = resolve_avatar_event([{
            "kind": "BRAIN_CHAT_RESPONSE_COMPLETED", "payload": {"ok": True},
            "created_at": now.isoformat(),
        }], now=now)
        failed = resolve_avatar_event([{
            "kind": "BRAIN_CHAT_REQUEST_FAILED", "payload": {},
            "created_at": now.isoformat(),
        }], now=now)
        self.assertEqual(started["state"], "THINKING")
        self.assertEqual(spoken["state"], "SPEAKING")
        self.assertEqual(failed["state"], "ERROR")

    def test_verification_event_maps_truthfully_and_stale_events_decay(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        success = resolve_avatar_event([{
            "kind": "BRAIN_SUPERVISOR_VERIFY",
            "payload": {"verified": True},
            "created_at": now.isoformat(),
        }], now=now)
        failure = resolve_avatar_event([{
            "kind": "BRAIN_SUPERVISOR_VERIFY",
            "payload": {"verified": False},
            "created_at": now.isoformat(),
        }], now=now)
        stale = resolve_avatar_event([{
            "kind": "BRAIN_SUPERVISOR_RUN_REQUESTED",
            "payload": {},
            "created_at": (now - timedelta(minutes=5)).isoformat(),
        }], now=now)
        self.assertEqual(success["state"], "SUCCESS")
        self.assertEqual(failure["state"], "ERROR")
        self.assertEqual(stale["state"], "IDLE")
        self.assertEqual(stale["source"], "no_recent_runtime_event")

    def test_malformed_or_unrelated_events_are_ignored(self):
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        result = resolve_avatar_event([
            {"kind": "BRAIN_SUPERVISOR_VERIFY", "payload": "{bad json", "created_at": now.isoformat()},
            {"kind": "UNRELATED_EVENT", "payload": {}, "created_at": now.isoformat()},
        ], now=now)
        self.assertEqual(result["state"], "IDLE")

    def test_ui_polls_real_endpoint_and_does_not_claim_connection_on_failure(self):
        self.assertIn("fetch('/api/brain-avatar/state'", self.html)
        self.assertIn("window.setInterval(pollLiveState,5000)", self.html)
        self.assertIn("Brain: تعذّر التحقق من الحالة الحية", self.html)
        self.assertIn('id="liveMode"', self.html)
        self.assertIn("brain.avatar.liveMode", self.html)
        self.assertIn("brain.avatar.label", self.html)
        self.assertIn('id="pulseText"', self.html)
        self.assertIn("data.human_presence_pulse", self.html)
        self.assertNotIn("ربطها بمحرك النبضات غير مفعّل بعد", self.html)
        self.assertLess(self.html.index("const names={"), self.html.index("if(!Object.prototype.hasOwnProperty.call(names,state.value))"))
        self.assertIn("savePref('brain.avatar.label',label.value)", self.html)
        self.assertIn("savePref('brain.avatar.liveMode','false')", self.html)

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
