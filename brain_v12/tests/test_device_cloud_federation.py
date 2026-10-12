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

    def test_verified_online_host_can_receive_allowed_work(self):
        host = DeviceEndpoint(
            endpoint_id="arkan-host-asus-vivobook",
            display_name="Optional physical execution host (ASUS VivoBook)",
            role=EndpointRole.COMPUTE_HOST,
            platform="windows",
            identity_verified=True,
            online=True,
            allowed_workloads=(Workload.BUILD_TEST,),
        )
        plan = plan_execution(Workload.BUILD_TEST, [host])
        self.assertEqual(plan.status, "LOCAL_TARGET_VERIFIED")
        self.assertEqual(plan.target, "arkan-host-asus-vivobook")

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

    def test_vehicle_endpoint_is_not_a_compute_executor(self):
        car = DeviceEndpoint(
            endpoint_id="honda-enp1-2023",
            display_name="Honda",
            role=EndpointRole.VEHICLE_CLIENT,
            platform="vehicle-infotainment",
            identity_verified=True,
            online=True,
            allowed_workloads=(Workload.CAR_COMPANION, Workload.BUILD_TEST),
        )
        plan = plan_execution(Workload.BUILD_TEST, [car])
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_EXECUTOR")

    def test_car_companion_is_allowed_only_as_a_limited_client(self):
        car = DeviceEndpoint(
            endpoint_id="honda-enp1-2023",
            display_name="Honda",
            role=EndpointRole.VEHICLE_CLIENT,
            platform="vehicle-infotainment",
            identity_verified=True,
            online=True,
            allowed_workloads=(Workload.CAR_COMPANION,),
        )
        plan = plan_execution(Workload.CAR_COMPANION, [car])
        self.assertEqual(plan.status, "LOCAL_TARGET_VERIFIED")
        self.assertEqual(plan.target, "honda-enp1-2023")




if __name__ == "__main__":
    unittest.main()
