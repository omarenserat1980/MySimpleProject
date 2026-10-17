from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.thermal_safety_policy import (
    CLOUD_SIMULATION,
    REAL_HARDWARE,
    thermal_sensor_policy_gate,
)


class ThermalSensorPolicyTests(unittest.TestCase):
    def test_cloud_simulation_does_not_require_physical_sensor(self):
        result = thermal_sensor_policy_gate(
            CLOUD_SIMULATION, sensor_required=True,
            sensor_available=False, sensor_reading_valid=False,
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["thermal_source"], "ESTIMATED")
        self.assertEqual(result["evidence_class"], "SIMULATION")
        self.assertFalse(result["physical_safety_claim"])

    def test_cloud_simulation_keeps_real_sensor_reading_distinct(self):
        result = thermal_sensor_policy_gate(
            CLOUD_SIMULATION, sensor_required=False,
            sensor_available=True, sensor_reading_valid=True,
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["thermal_source"], "REAL_SENSOR")

    def test_required_real_hardware_sensor_missing_fails_closed(self):
        result = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=True,
            sensor_available=False, sensor_reading_valid=False,
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["status"], "BLOCKED_REQUIRED_THERMAL_SENSOR")

    def test_required_real_hardware_sensor_invalid_fails_closed(self):
        result = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=True,
            sensor_available=True, sensor_reading_valid=False,
        )
        self.assertFalse(result["allowed"])

    def test_verified_real_sensor_satisfies_sensor_requirement(self):
        result = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=True,
            sensor_available=True, sensor_reading_valid=True,
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["thermal_source"], "REAL_SENSOR")

    def test_approved_alternative_must_be_explicit(self):
        blocked = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=True,
            sensor_available=False, sensor_reading_valid=False,
        )
        allowed = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=True,
            sensor_available=False, sensor_reading_valid=False,
            approved_alternative=True,
        )
        self.assertFalse(blocked["allowed"])
        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["thermal_source"], "APPROVED_ALTERNATIVE")

    def test_sensor_not_mandated_does_not_fabricate_a_reading(self):
        result = thermal_sensor_policy_gate(
            REAL_HARDWARE, sensor_required=False,
            sensor_available=False, sensor_reading_valid=False,
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["thermal_source"], "NOT_REQUIRED_BY_POLICY")

    def test_unknown_mode_fails_closed(self):
        result = thermal_sensor_policy_gate(
            "UNKNOWN", sensor_required=False,
            sensor_available=True, sensor_reading_valid=True,
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["evidence_class"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
