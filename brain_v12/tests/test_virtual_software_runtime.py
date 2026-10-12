import unittest

from brain_v12.virtual_software.runtime import VirtualSoftwareRuntime


class VirtualSoftwareRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = VirtualSoftwareRuntime()

    def test_catalog_has_multiple_real_world_application_classes(self):
        profiles = {p["category"] for p in self.runtime.profiles()}
        self.assertTrue({"browser", "office", "database", "media", "developer-tools"} <= profiles)

    def test_lifecycle_and_declared_action_are_deterministic(self):
        self.runtime.create("browser-1", "browser-workflow-v1")
        app = self.runtime.get("browser-1")
        self.assertTrue(app.start({"powered": True, "capabilities": ["filesystem"]})["ok"])
        action = app.perform("URL/navigation state", {"url": "https://example.invalid"})
        self.assertEqual(action["status"], "SIMULATED")
        self.assertFalse(action["external_side_effects"])
        self.assertEqual(action["payload_sha256"], app.perform(
            "URL/navigation state", {"url": "https://example.invalid"})["payload_sha256"])

    def test_missing_capability_blocks_start(self):
        self.runtime.create("media-1", "media-workflow-v1")
        result = self.runtime.get("media-1").start({"powered": True, "capabilities": ["filesystem"]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "APPLICATION_CAPABILITIES_MISSING")

    def test_arbitrary_actions_and_non_json_payloads_are_rejected(self):
        self.runtime.create("office-1", "office-workflow-v1")
        app = self.runtime.get("office-1")
        app.start({"powered": True, "capabilities": ["filesystem"]})
        self.assertEqual(app.perform("execute arbitrary shell", {})["reason"], "UNSUPPORTED_ACTION")
        self.assertEqual(app.perform("document create/edit/save", {"bad": object()})["reason"],
                         "PAYLOAD_NOT_JSON_SAFE")

    def test_duplicate_and_unknown_profiles_are_rejected(self):
        self.runtime.create("app-1", "office-workflow-v1")
        with self.assertRaisesRegex(ValueError, "VIRTUAL_APPLICATION_ALREADY_EXISTS"):
            self.runtime.create("app-1", "office-workflow-v1")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_APPLICATION_PROFILE"):
            self.runtime.create("app-2", "unknown-vendor-app")


if __name__ == "__main__":
    unittest.main()
