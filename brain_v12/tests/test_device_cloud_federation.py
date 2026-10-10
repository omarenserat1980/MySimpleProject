import unittest

from brain_v12.brain.device_cloud_federation import (
    DeviceEndpoint, EndpointRole, Workload, default_fleet, plan_execution,
)


class DeviceCloudFederationTests(unittest.TestCase):
    def test_default_fleet_is_inventory_not_fabricated_liveness(self):
        fleet = default_fleet()
        self.assertEqual(
            [item.endpoint_id for item in fleet],
            ["arkan", "redmi3-01", "realme-pending-identity", "honda-enp1-2023"],
        )
        self.assertTrue(all(not item.online for item in fleet))
        self.assertTrue(all(not item.identity_verified for item in fleet))

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
            endpoint_id="arkan",
            display_name="Arkan",
            role=EndpointRole.COMPUTE_HOST,
            platform="windows",
            identity_verified=True,
            online=True,
            allowed_workloads=(Workload.BUILD_TEST,),
        )
        plan = plan_execution(Workload.BUILD_TEST, [host])
        self.assertEqual(plan.status, "LOCAL_TARGET_VERIFIED")
        self.assertEqual(plan.target, "arkan")

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


    def test_fleet_status_reports_live_heartbeat_without_claiming_identity(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status
        result = build_fleet_status({
            "ttl_seconds": 15,
            "agents": [
                {"agent_id": "redmi3-01", "online": True, "age_seconds": 2.5},
                {"agent_id": "other-device", "online": True, "age_seconds": 1.0},
                {"agent_id": "realme-pending-identity", "online": False, "age_seconds": 90.0},
            ],
        })
        rows = {row["endpoint_id"]: row for row in result["fleet"]}
        self.assertEqual(rows["redmi3-01"]["observed_state"], "ONLINE")
        self.assertFalse(rows["redmi3-01"]["identity_verified"])
        self.assertFalse(rows["redmi3-01"]["execution_eligible"])
        self.assertEqual(rows["realme-pending-identity"]["observed_state"], "STALE")
        self.assertEqual(rows["arkan"]["observed_state"], "NOT_OBSERVED")
        self.assertFalse(result["cloud"]["capacity_verified"])
        self.assertFalse(result["cloud"]["paid_provisioning_allowed"])


if __name__ == "__main__":
    unittest.main()
