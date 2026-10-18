import copy
import unittest

from brain_v12.virtual_hardware.cluster_manager import BrainVirtualClusterManager


class BrainVirtualClusterManagerTests(unittest.TestCase):
    def test_round_robin_places_tasks_on_ready_nodes(self):
        cluster = BrainVirtualClusterManager(ram_cells_per_task=16)
        cluster.add_node("n1")
        cluster.add_node("n2")
        first = cluster.place_task("a", [("HALT",)])
        second = cluster.place_task("b", [("HALT",)])
        self.assertEqual(first["node_id"], "n1")
        self.assertEqual(second["node_id"], "n2")
        self.assertFalse(first["physical_hardware"])

    def test_failed_or_draining_nodes_do_not_receive_new_tasks(self):
        cluster = BrainVirtualClusterManager(ram_cells_per_task=16)
        cluster.add_node("n1")
        cluster.add_node("n2")
        cluster.set_node_state("n1", "FAILED")
        cluster.set_node_state("n2", "DRAINING")
        with self.assertRaisesRegex(RuntimeError, "NO_READY_NODES"):
            cluster.place_task("task", [("HALT",)])

    def test_checkpoint_restores_hosts_and_task_programs(self):
        cluster = BrainVirtualClusterManager(cluster_id="test-cluster", ram_cells_per_task=16)
        cluster.add_node("n1")
        cluster.place_task("loop", [("MOVI", 0, 8), ("OUT", 0), ("JMP", 2)])
        cluster.run_node("n1", max_ticks=4)
        snapshot = cluster.checkpoint()
        restored = BrainVirtualClusterManager(ram_cells_per_task=16)
        restored.restore_checkpoint(snapshot)
        self.assertEqual(restored.checkpoint(), snapshot)
        a = cluster.run_node("n1", max_ticks=5)
        b = restored.run_node("n1", max_ticks=5)
        self.assertEqual(a["trace"], b["trace"])
        self.assertEqual(a["tasks"], b["tasks"])

    def test_bad_checkpoint_does_not_mutate_cluster(self):
        cluster = BrainVirtualClusterManager(cluster_id="stable", ram_cells_per_task=16)
        cluster.add_node("n1")
        before = cluster.checkpoint()
        invalid = copy.deepcopy(before)
        invalid["nodes"][0]["state"] = "MAGIC"
        with self.assertRaisesRegex(ValueError, "NODE_STATE_INVALID"):
            cluster.restore_checkpoint(invalid)
        self.assertEqual(cluster.checkpoint(), before)

    def test_no_ready_nodes_is_not_reported_as_healthy(self):
        cluster = BrainVirtualClusterManager(ram_cells_per_task=16)
        self.assertFalse(cluster.health()["ok"])
        cluster.add_node("n1")
        cluster.set_node_state("n1", "FAILED")
        self.assertFalse(cluster.health()["ok"])


if __name__ == "__main__":
    unittest.main()
