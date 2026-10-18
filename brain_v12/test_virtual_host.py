import copy
import unittest

from brain_v12.virtual_hardware.virtual_host import BrainVirtualHost


class BrainVirtualHostTests(unittest.TestCase):
    def test_integrates_task_scheduler_and_service_runtime(self):
        host = BrainVirtualHost(ram_cells_per_task=16)
        host.register_service("control", "api")
        host.start_service("control")
        host.create_task("calc", [("MOVI", 0, 9), ("OUT", 0), ("HALT",)])
        task_result = host.run_tasks(max_ticks=5)
        response = host.request("control", "health")
        health = host.health()
        self.assertTrue(task_result["completed"])
        self.assertTrue(response["ok"])
        self.assertEqual(health["mode"], "SIMULATED_BRAIN_VIRTUAL_HOST")
        self.assertFalse(health["network_listener_enabled"])
        self.assertFalse(health["physical_hardware"])

    def test_checkpoint_restores_services_but_does_not_claim_task_resume(self):
        host = BrainVirtualHost(host_id="host-A", ram_cells_per_task=16)
        host.register_service("api", "api")
        host.start_service("api")
        host.create_task("pending", [("JMP", 0)])
        snapshot = host.checkpoint()

        restored = BrainVirtualHost(ram_cells_per_task=16)
        result = restored.restore_checkpoint(snapshot)
        self.assertEqual(result["host_id"], "host-A")
        self.assertEqual(result["server"]["running_services"], 1)
        self.assertEqual(result["restored_task_snapshots"], 1)
        self.assertFalse(result["tasks_resumed"])
        self.assertEqual(result["reason"], "PROGRAMS_NOT_INCLUDED_IN_HOST_CHECKPOINT")

    def test_bad_checkpoint_is_rejected_without_mutating_host(self):
        host = BrainVirtualHost(host_id="stable", ram_cells_per_task=16)
        before = host.health()
        invalid = {"schema": "wrong", "mode": "SIMULATED_BRAIN_VIRTUAL_HOST"}
        with self.assertRaisesRegex(ValueError, "SCHEMA_UNSUPPORTED"):
            host.restore_checkpoint(invalid)
        self.assertEqual(host.health(), before)

    def test_task_checkpoint_counter_mismatch_is_rejected(self):
        host = BrainVirtualHost(ram_cells_per_task=16)
        host.create_task("loop", [("JMP", 0)])
        snapshot = copy.deepcopy(host.checkpoint())
        snapshot["task_manifest"][0]["instructions_executed"] = 99
        restored = BrainVirtualHost(ram_cells_per_task=16)
        with self.assertRaisesRegex(ValueError, "COUNTER_MISMATCH"):
            restored.restore_checkpoint(snapshot)


if __name__ == "__main__":
    unittest.main()
