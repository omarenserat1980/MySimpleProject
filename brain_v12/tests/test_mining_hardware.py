import unittest

from brain_v12.virtual_hardware.mining_hardware import (
    DEFAULT_ASIC_PROFILES,
    MinerState,
    VirtualASICMiner,
)


class VirtualASICMinerTests(unittest.TestCase):
    def test_profiles_are_valid_and_explicitly_estimated(self):
        for profile in DEFAULT_ASIC_PROFILES.values():
            profile.validate()
            self.assertIn("estimate", profile.source_kind)

    def test_start_and_tick_simulate_hash_rate_and_power(self):
        miner = VirtualASICMiner(DEFAULT_ASIC_PROFILES["asic_midrange"])
        self.assertEqual(miner.start()["state"], MinerState.MINING_SIMULATED.value)
        result = miner.tick(5)
        self.assertGreater(result["estimated"]["hash_rate_th_s"], 0)
        self.assertGreater(result["estimated"]["power_w"], 0)
        self.assertFalse(result["estimated"]["is_calibrated"])
        self.assertFalse(result["work_simulation"]["real_bitcoin_mining"])

    def test_failed_hashboard_reduces_hash_rate(self):
        miner = VirtualASICMiner(DEFAULT_ASIC_PROFILES["asic_midrange"])
        miner.start()
        full_rate = miner.tick()["estimated"]["hash_rate_th_s"]
        miner.inject_fault("hashboard", 0)
        reduced_rate = miner.tick()["estimated"]["hash_rate_th_s"]
        self.assertLess(reduced_rate, full_rate)

    def test_network_failure_stops_simulated_hashing(self):
        miner = VirtualASICMiner()
        miner.start()
        miner.inject_fault("network", enabled=True)
        result = miner.tick()
        self.assertEqual(result["state"], MinerState.FAULT.value)
        self.assertEqual(result["estimated"]["hash_rate_th_s"], 0)
        self.assertIn("network_unavailable", result["faults"])

    def test_fan_fault_is_reported_and_power_loss_stops_miner(self):
        miner = VirtualASICMiner()
        miner.start()
        miner.inject_fault("fan", 0)
        self.assertEqual(miner.tick()["hardware"]["fans"], miner.profile.fan_count)
        miner.inject_fault("power_loss", enabled=True)
        result = miner.tick()
        self.assertEqual(result["state"], MinerState.FAULT.value)
        self.assertEqual(result["estimated"]["hash_rate_th_s"], 0)

    def test_stop_and_work_accounting(self):
        miner = VirtualASICMiner()
        miner.start()
        miner.submit_simulated_work(3)
        miner.submit_simulated_work(2, accepted=False)
        result = miner.snapshot()
        self.assertEqual(result["work_simulation"]["accepted_units"], 3)
        self.assertEqual(result["work_simulation"]["rejected_units"], 2)
        self.assertEqual(miner.stop()["state"], MinerState.OFF.value)

    def test_rejects_invalid_tick_and_fault(self):
        miner = VirtualASICMiner()
        with self.assertRaises(ValueError):
            miner.tick(0)
        with self.assertRaises(ValueError):
            miner.inject_fault("hashboard", 999)


if __name__ == "__main__":
    unittest.main()
