import unittest

from brain_v12.brain.device_cloud_federation import (
    DeviceEndpoint, EndpointRole, Workload, default_fleet, plan_execution,
)


class DeviceCloudFederationTests(unittest.TestCase):
    def test_default_fleet_is_inventory_not_fabricated_liveness(self):
        fleet = default_fleet()
        self.assertEqual(
            [item.endpoint_id for item in fleet],
            ["arkan-virtual-01", "redmi3-01", "realme-pending-identity", "honda-enp1-2023"],
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

    def test_arkan_virtual_runtime_is_ready_only_with_live_simulator_and_task_evidence(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status

        not_running = build_fleet_status(
            {"ttl_seconds": 15, "agents": []},
            {
                "exists": True,
                "device_id": "arkan-virtual-01",
                "identity_independent_of_host": True,
                "runtime_loaded": False,
                "simulator_booted": False,
                "native_os_boot_verified": False,
                "task_execution_evidence": {"status": "PASS"},
            },
        )
        row = next(x for x in not_running["fleet"] if x["endpoint_id"] == "arkan-virtual-01")
        self.assertEqual(row["observed_state"], "CONFIGURED_NOT_RUNNING")
        self.assertFalse(row["execution_eligible"])
        self.assertFalse(row["native_os_boot_verified"])

        ready = build_fleet_status(
            {"ttl_seconds": 15, "agents": []},
            {
                "exists": True,
                "device_id": "arkan-virtual-01",
                "identity_independent_of_host": True,
                "runtime_loaded": True,
                "simulator_booted": True,
                "native_os_boot_verified": False,
                "runtime_status": {"powered": True},
                "task_execution_evidence": {"status": "PASS"},
            },
        )
        row = next(x for x in ready["fleet"] if x["endpoint_id"] == "arkan-virtual-01")
        self.assertEqual(row["observed_state"], "SIMULATION_READY")
        self.assertTrue(row["identity_verified"])
        self.assertTrue(row["execution_eligible"])
        self.assertEqual(row["supported_execution"], ["bounded_symbolic_virtual_simulation"])
        self.assertFalse(row["native_os_boot_verified"])

    def test_wrong_arkan_identity_cannot_be_marked_ready(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status

        result = build_fleet_status(
            {"ttl_seconds": 15, "agents": []},
            {
                "exists": True,
                "device_id": "arkan-host-asus-vivobook",
                "identity_independent_of_host": True,
                "runtime_loaded": True,
                "simulator_booted": True,
                "runtime_status": {"powered": True},
                "task_execution_evidence": {"status": "PASS"},
            },
        )
        row = next(x for x in result["fleet"] if x["endpoint_id"] == "arkan-virtual-01")
        self.assertFalse(row["identity_verified"])
        self.assertFalse(row["execution_eligible"])
        self.assertNotEqual(row["observed_state"], "SIMULATION_READY")

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
        self.assertEqual(rows["arkan-virtual-01"]["observed_state"], "NOT_PROVISIONED")
        self.assertEqual(rows["arkan-virtual-01"]["role"], "virtual_computer")
        self.assertEqual(rows["arkan-virtual-01"]["platform"], "brain-simulator")
        self.assertEqual(rows["arkan-virtual-01"]["allowed_workloads"], ["virtual_simulation"])
        self.assertFalse(rows["arkan-virtual-01"]["execution_eligible"])
        self.assertFalse(result["cloud"]["capacity_verified"])
        self.assertFalse(result["cloud"]["paid_provisioning_allowed"])


if __name__ == "__main__":
    unittest.main()
