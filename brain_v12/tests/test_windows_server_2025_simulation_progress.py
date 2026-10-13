import unittest

from brain_v12.brain.windows_server_2025_simulation_progress import (
    MILESTONES,
    simulation_progress_snapshot,
)


class WindowsServer2025SimulationProgressTests(unittest.TestCase):
    def test_progress_is_evidence_bounded_to_eighteen_percent(self):
        progress = simulation_progress_snapshot()
        self.assertEqual(progress["percent"], 18)
        self.assertEqual(progress["completed_weight"], 18)
        self.assertEqual(progress["total_weight"], 100)
        self.assertEqual(sum(item["weight"] for item in MILESTONES), 100)
        self.assertEqual(
            sum(item["weight"] for item in MILESTONES if item["status"] == "complete"),
            18,
        )
        self.assertEqual(progress["execution_mode"], "SIMULATION_ONLY")
        self.assertIs(progress["real_windows_boot_verified"], False)

    def test_only_explicitly_implemented_milestones_are_complete(self):
        complete = [item["id"] for item in MILESTONES if item["status"] == "complete"]
        self.assertEqual(complete, [
            "simulation_safety_boundary",
            "virtual_hardware_preflight",
            "boot_state_machine_and_faults",
        ])
        self.assertTrue(all(item["status"] == "pending"
                            for item in MILESTONES if item["id"] not in complete))


if __name__ == "__main__":
    unittest.main()
