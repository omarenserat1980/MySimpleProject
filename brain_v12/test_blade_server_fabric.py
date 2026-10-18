import copy
import unittest

from brain_v12.virtual_hardware.blade_server_fabric import BrainBladeServerFabric


class BrainBladeServerFabricTests(unittest.TestCase):
    def test_places_tasks_and_runs_blade(self):
        fabric = BrainBladeServerFabric(ram_cells_per_task=16, task_slots_per_blade=4)
        fabric.add_blade("b1", node_count=2)
        placed = fabric.place_task("halt", [("HALT",)])
        self.assertEqual(placed["blade_id"], "b1")
        self.assertFalse(placed["physical_hardware"])
        result = fabric.run_blade("b1", max_ticks=4)
        self.assertEqual(result["mode"], "SIMULATED_BLADE_RUN")

    def test_failure_is_isolated_and_blocks_new_placement(self):
        fabric = BrainBladeServerFabric(ram_cells_per_task=16)
        fabric.add_blade("b1")
        fabric.add_blade("b2")
        fabric.set_blade_state("b1", "FAILED")
        placed = fabric.place_task("survivor", [("HALT",)])
        self.assertEqual(placed["blade_id"], "b2")
        with self.assertRaisesRegex(RuntimeError, "BLADE_NOT_ONLINE"):
            fabric.run_blade("b1")

    def test_draining_blade_is_not_selected(self):
        fabric = BrainBladeServerFabric(ram_cells_per_task=16)
        fabric.add_blade("b1")
        fabric.add_blade("b2")
        fabric.set_blade_state("b1", "DRAINING")
        self.assertEqual(fabric.place_task("task", [("HALT",)])["blade_id"], "b2")

    def test_checkpoint_restores_tasks_and_blade_states(self):
        fabric = BrainBladeServerFabric(fabric_id="test-fabric", ram_cells_per_task=16)
        fabric.add_blade("b1", node_count=2)
        fabric.place_task("loop", [("MOVI", 0, 3), ("OUT", 0), ("JMP", 2)])
        fabric.run_blade("b1", max_ticks=3)
        fabric.add_blade("b2")
        fabric.set_blade_state("b2", "DRAINING")
        snapshot = fabric.checkpoint()
        restored = BrainBladeServerFabric(ram_cells_per_task=16)
        restored.restore_checkpoint(snapshot)
        self.assertEqual(restored.checkpoint(), snapshot)
        a = fabric.run_blade("b1", max_ticks=5)
        b = restored.run_blade("b1", max_ticks=5)
        self.assertEqual(a, b)

    def test_invalid_checkpoint_does_not_mutate_fabric(self):
        fabric = BrainBladeServerFabric(fabric_id="stable", ram_cells_per_task=16)
        fabric.add_blade("b1")
        before = fabric.checkpoint()
        bad = copy.deepcopy(before)
        bad["blades"][0]["state"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "BLADE_STATE_INVALID"):
            fabric.restore_checkpoint(bad)
        self.assertEqual(fabric.checkpoint(), before)

    def test_task_slot_limit_is_enforced(self):
        fabric = BrainBladeServerFabric(ram_cells_per_task=16, task_slots_per_blade=1)
        fabric.add_blade("b1")
        fabric.place_task("first", [("HALT",)])
        with self.assertRaisesRegex(RuntimeError, "NO_CAPACITY"):
            fabric.place_task("second", [("HALT",)])


if __name__ == "__main__":
    unittest.main()
