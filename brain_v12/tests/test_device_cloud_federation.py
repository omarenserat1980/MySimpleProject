import unittest

from brain_v12.brain.device_cloud_federation import (
    DeviceEndpoint, EndpointRole, Workload, default_fleet, plan_execution,
)


class DeviceCloudFederationTests(unittest.TestCase):
    def test_default_fleet_contains_only_software_nodes(self):
        fleet = default_fleet()
        ids = [item.endpoint_id for item in fleet]
        self.assertEqual(
            ids,
            ["brain-control-plane-main", "arkan-software-executor", "github-actions-runner"],
        )
        forbidden = ("redmi", "realme", "honda", "android", "termux", "hardware")
        self.assertFalse(any(any(token in item.endpoint_id.lower() for token in forbidden) for item in fleet))

    def test_unverified_devices_do_not_receive_work(self):
        plan = plan_execution(Workload.BUILD_TEST)
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_EXECUTOR")
        self.assertIsNone(plan.target)

    def test_cloud_fallback_requires_both_capacity_and_free_gate(self):
        self.assertEqual(
            plan_execution(Workload.AI_INFERENCE, cloud_capacity_verified=True).status,
            "BLOCKED_NO_VERIFIED_EXECUTOR",
        )
        plan = plan_execution(
            Workload.AI_INFERENCE,
            cloud_capacity_verified=True,
            free_cost_gate_passed=True,
        )
        self.assertEqual(plan.status, "CLOUD_TARGET_VERIFIED")
        self.assertEqual(plan.target, "brain-cloud-free-pool")

    def test_status_ignores_legacy_hardware_heartbeats_and_runtime(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status
        result = build_fleet_status(
            {"ttl_seconds": 15, "agents": [{"agent_id": "redmi3-01", "online": True, "age_seconds": 1}]},
            {
                "exists": True,
                "device_id": "arkan-virtual-01",
                "identity_independent_of_host": True,
                "runtime_loaded": True,
                "simulator_booted": True,
                "runtime_status": {"powered": True},
                "task_execution_evidence": {"status": "PASS"},
            },
        )
        self.assertEqual(result["mode"], "software-only")
        self.assertFalse(result["hardware_indicators_enabled"])
        self.assertEqual(result["hardware_nodes"], [])
        rows = {row["endpoint_id"]: row for row in result["fleet"]}
        self.assertEqual(set(rows), {"brain-control-plane-main", "arkan-software-executor", "github-actions-runner"})
        self.assertEqual(rows["arkan-software-executor"]["observed_state"], "NOT_PROBED")
        self.assertFalse(any(row["execution_eligible"] for row in rows.values()))
        self.assertFalse(any("redmi" in row["endpoint_id"] for row in result["fleet"]))


if __name__ == "__main__":
    unittest.main()
