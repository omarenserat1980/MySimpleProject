import unittest

from brain_v12.virtual_hardware.mining_farm import VirtualMiningFarm
from brain_v12.virtual_hardware.mining_hardware import DEFAULT_ASIC_PROFILES


class VirtualMiningFarmTests(unittest.TestCase):
    def test_multi_node_inventory_aggregation_and_energy(self):
        farm = VirtualMiningFarm()
        farm.add_miner("asic-01", profile=DEFAULT_ASIC_PROFILES["asic_entry"], rack_id="rack-a")
        farm.add_miner("asic-02", profile=DEFAULT_ASIC_PROFILES["asic_midrange"], rack_id="rack-b")
        started = farm.start_all()
        self.assertEqual(started["active_node_count"], 2)
        result = farm.tick(10)
        self.assertGreater(result["estimated"]["hash_rate_th_s"], 0)
        self.assertGreater(result["estimated"]["energy_wh"], 0)
        self.assertFalse(result["estimated"]["calibrated"])
        self.assertFalse(result["real_bitcoin_mining"])

    def test_simulated_job_never_uses_network(self):
        farm = VirtualMiningFarm()
        farm.add_miner("asic-01")
        farm.start_all()
        job = farm.assign_simulated_job("job-test-1")
        self.assertTrue(job["simulated_pool"]["connected"])
        self.assertFalse(job["external_network_used"])
        self.assertFalse(farm.snapshot()["real_bitcoin_mining"])

    def test_disable_node_and_stop_all(self):
        farm = VirtualMiningFarm()
        farm.add_miner("asic-01")
        farm.start_all()
        farm.set_node_enabled("asic-01", False)
        self.assertEqual(farm.snapshot()["active_node_count"], 0)
        self.assertEqual(farm.stop_all()["simulated_pool"]["connected"], False)

    def test_duplicate_node_and_invalid_tick_rejected(self):
        farm = VirtualMiningFarm()
        farm.add_miner("asic-01")
        with self.assertRaises(ValueError):
            farm.add_miner("asic-01")
        with self.assertRaises(ValueError):
            farm.tick(0)

    def test_job_requires_active_worker(self):
        farm = VirtualMiningFarm()
        farm.add_miner("asic-01")
        with self.assertRaises(RuntimeError):
            farm.assign_simulated_job("job-test")


if __name__ == "__main__":
    unittest.main()
