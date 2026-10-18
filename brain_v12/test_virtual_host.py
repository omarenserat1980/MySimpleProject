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

    def test_checkpoint_restores_services_and_resumes_task_programs(self):
        host = BrainVirtualHost(host_id="host-A", ram_cells_per_task=16)
        host.register_service("api", "api")
        host.start_service("api")
        host.create_task("pending", [("MOVI", 0, 4), ("OUT", 0), ("JMP", 2)])
        host.run_tasks(max_ticks=4)
        snapshot = host.checkpoint()

        restored = BrainVirtualHost(ram_cells_per_task=16)
        result = restored.restore_checkpoint(snapshot)
        self.assertEqual(result["host_id"], "host-A")
        self.assertEqual(result["server"]["running_services"], 1)
        self.assertEqual(result["restored_task_count"], 1)
        self.assertTrue(result["tasks_resumed"])
        self.assertEqual(restored.checkpoint()["task_runner"], snapshot["task_runner"])

        original_next = host.run_tasks(max_ticks=8)
        restored_next = restored.run_tasks(max_ticks=8)
        self.assertEqual(original_next["trace"], restored_next["trace"])
        self.assertEqual(original_next["tasks"], restored_next["tasks"])
        self.assertEqual(restored.request("api", "health")["request_number"], 1)

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
        snapshot["task_runner"]["tasks"][0]["steps"] = 99
        restored = BrainVirtualHost(ram_cells_per_task=16)
        before = restored.checkpoint()
        with self.assertRaisesRegex(ValueError, "STEP_COUNT_MISMATCH"):
            restored.restore_checkpoint(snapshot)
        self.assertEqual(restored.checkpoint(), before)

    def test_host_server_id_mismatch_is_rejected(self):
        host = BrainVirtualHost(host_id="host-A", ram_cells_per_task=16)
        snapshot = copy.deepcopy(host.checkpoint())
        snapshot["host_id"] = "different-host"
        restored = BrainVirtualHost(ram_cells_per_task=16)
        with self.assertRaisesRegex(ValueError, "SERVER_ID_MISMATCH"):
            restored.restore_checkpoint(snapshot)


if __name__ == "__main__":
    unittest.main()
