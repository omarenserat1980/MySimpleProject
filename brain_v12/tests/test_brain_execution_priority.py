import unittest

from brain_v12.tools.brain_execution_priority import choose_execution_channel


class BrainExecutionPriorityTests(unittest.TestCase):
    def test_brain_local_wins_when_available(self):
        result = choose_execution_channel({"channels": {
            "brain_local": {"available": True, "reason": "runtime ready"},
            "github_actions_arkan": {"available": True},
            "desktop_commander": {"available": True, "quota_available": True},
        }})
        self.assertEqual(result["selected"], "brain_local")

    def test_github_runner_precedes_termux_and_desktop(self):
        result = choose_execution_channel({"channels": {
            "github_actions_arkan": {"available": True},
            "termux_agent": {"available": True},
            "desktop_commander": {"available": True, "quota_available": True},
        }})
        self.assertEqual(result["selected"], "github_actions_arkan")

    def test_exhausted_desktop_quota_is_never_selected(self):
        result = choose_execution_channel({"channels": {
            "desktop_commander": {"available": True, "quota_available": False},
        }})
        self.assertFalse(result["ok"])
        self.assertIsNone(result["selected"])

    def test_unknown_or_stale_channels_fail_closed(self):
        result = choose_execution_channel({"channels": {
            "brain_local": {"available": "unknown"},
            "termux_agent": {"available": False},
        }})
        self.assertFalse(result["ok"])

    def test_fallback_order_reaches_termux_before_desktop(self):
        result = choose_execution_channel({"channels": {
            "termux_agent": {"available": True},
            "desktop_commander": {"available": True, "quota_available": True},
        }})
        self.assertEqual(result["selected"], "termux_agent")
        self.assertFalse(result["execution_performed"])


if __name__ == "__main__":
    unittest.main()
