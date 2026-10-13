from __future__ import annotations

import unittest

from brain3_mouse.unified_kernel import ComponentAdapter, UnifiedBrainKernel


class UnifiedKernelTests(unittest.TestCase):
    def setUp(self):
        self.kernel = UnifiedBrainKernel()

    def test_one_memory_store_is_shared(self):
        self.kernel.memory_set("shared:goal", {"text": "unify"})
        self.assertEqual(self.kernel.memory_get("shared:goal"), {"text": "unify"})

    def test_one_queue_accepts_tasks_without_separate_brain_queues(self):
        old_task = self.kernel.submit("inspect", "legacy request", "legacy_brain")
        new_task = self.kernel.submit("plan", "v12 request", "brain_v12")
        self.assertEqual(old_task["queue"], "brain3_shared")
        self.assertEqual(new_task["queue"], "brain3_shared")
        self.assertEqual([t["id"] for t in self.kernel.tasks()], [1, 2])

    def test_unverified_adapter_cannot_dispatch(self):
        task = self.kernel.submit("inspect", "safe check")
        self.kernel.register_adapter(ComponentAdapter(
            name="brain_v12", capabilities=frozenset({"inspect"}),
            handler=lambda action, payload: {"ok": True}, verified=False,
        ))
        with self.assertRaisesRegex(PermissionError, "not registered and verified"):
            self.kernel.dispatch(task["id"], "brain_v12")

    def test_verified_in_process_adapter_uses_shared_task(self):
        task = self.kernel.submit("inspect", "safe check")
        self.kernel.register_adapter(ComponentAdapter(
            name="brain_v12", capabilities=frozenset({"inspect"}),
            handler=lambda action, payload: {"action": action, "shared": True}, verified=True,
        ))
        result = self.kernel.dispatch(task["id"], "brain_v12")
        self.assertEqual(result["state"], "COMPLETED")
        self.assertEqual(result["queue"], "brain3_shared")
        self.assertTrue(result["executed"])

    def test_forbidden_actions_fail_closed(self):
        for action in ("execute", "deploy", "render", "windows_boot", "device_setup", "publish"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    self.kernel.submit(action, "must be blocked")

    def test_health_does_not_claim_missing_runtime_integrations(self):
        health = self.kernel.health()
        self.assertFalse(health["legacy_brain_integrated"])
        self.assertFalse(health["brain_v12_integrated"])
        self.assertFalse(health["render"])
        self.assertFalse(health["windows_boot_verified"])
        self.assertFalse(health["production_ready"])


if __name__ == "__main__":
    unittest.main()
