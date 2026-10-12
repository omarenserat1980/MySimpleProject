import unittest

from brain_v12.brain.device_cloud_federation import (
    DeviceEndpoint, EndpointRole, Workload, default_fleet, plan_execution,
)


class DeviceCloudFederationTests(unittest.TestCase):
    def test_default_fleet_is_inventory_not_fabricated_liveness(self):
        fleet = default_fleet()
        self.assertEqual(
            [item.endpoint_id for item in fleet],
            ["arkan-virtual-01", "phone-virtual-01"],
        )
        self.assertTrue(all(not item.online for item in fleet))
        self.assertTrue(all(not item.identity_verified for item in fleet))

    def test_live_fleet_inspection_records_observation_timestamps_for_virtual_nodes(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status

        result = build_fleet_status({"ttl_seconds": 15, "agents": []})
        for row in result["fleet"]:
            if row["role"] in {"virtual_computer", "virtual_phone"}:
                self.assertTrue(row["observed_at"].endswith("Z"))
                self.assertEqual(row["reality"], "SIMULATED")

    def test_unverified_devices_do_not_receive_work(self):
        plan = plan_execution(Workload.BUILD_TEST)
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")
        self.assertIsNone(plan.target)

    def test_cloud_fallback_requires_both_capacity_and_free_gate(self):
        self.assertEqual(
            plan_execution(Workload.AI_INFERENCE, cloud_capacity_verified=True).status,
            "BLOCKED_NO_VERIFIED_SOFTWARE_NODE",
        )
        plan = plan_execution(
            Workload.AI_INFERENCE,
            cloud_capacity_verified=True,
            free_cost_gate_passed=True,
        )
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")
        self.assertIsNone(plan.target)
        self.assertIn("cloud_fallback_disabled_in_software_only_mode", plan.reasons)

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
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")
        self.assertIsNone(plan.target)

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

    def test_virtual_phone_requires_live_simulator_and_task_evidence_for_readiness(self):
        from brain_v12.brain.device_cloud_federation import build_fleet_status

        configured = build_fleet_status({"ttl_seconds": 15, "agents": []})
        row = next(x for x in configured["fleet"] if x["endpoint_id"] == "phone-virtual-01")
        self.assertEqual(row["observed_state"], "PROFILE_REGISTERED_NOT_RUNNING")
        self.assertFalse(row["execution_eligible"])

        ready = build_fleet_status(
            {"ttl_seconds": 15, "agents": []},
            virtual_phone_status={
                "exists": True,
                "device_id": "phone-virtual-01",
                "identity_independent_of_host": True,
                "runtime_loaded": True,
                "simulator_booted": True,
                "runtime_status": {"powered": True},
                "task_execution_evidence": {"status": "PASS"},
            },
        )
        row = next(x for x in ready["fleet"] if x["endpoint_id"] == "phone-virtual-01")
        self.assertEqual(row["observed_state"], "SIMULATION_READY")
        self.assertTrue(row["execution_eligible"])
        self.assertFalse(row["native_os_boot_verified"])
        self.assertEqual(ready["active_software_node"]["indicator_target"], "arkan-virtual-01")
        self.assertNotEqual(ready["active_software_node"]["indicator_state"], "SIMULATION_READY")

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

    def test_physical_host_cannot_receive_work_in_software_only_mode(self):
        host = DeviceEndpoint(
            endpoint_id="arkan-host-asus-vivobook",
            display_name="Physical Arkan host",
            role=EndpointRole.COMPUTE_HOST,
            platform="windows",
            identity_verified=True,
            online=True,
            allowed_workloads=(Workload.BUILD_TEST,),
        )
        plan = plan_execution(Workload.BUILD_TEST, [host])
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")
        self.assertIsNone(plan.target)

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
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")

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
        self.assertEqual(plan.status, "BLOCKED_NO_VERIFIED_SOFTWARE_NODE")
        self.assertIsNone(plan.target)


    def test_fleet_status_indicators_only_include_software_nodes(self):
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
        self.assertEqual(rows["phone-virtual-01"]["observed_state"], "PROFILE_REGISTERED_NOT_RUNNING")
        self.assertEqual(rows["phone-virtual-01"]["role"], "virtual_phone")
        self.assertEqual(rows["phone-virtual-01"]["platform"], "brain-mobile-simulator")
        self.assertFalse(rows["phone-virtual-01"]["indicator_selected"])
        self.assertFalse(rows["phone-virtual-01"]["physical_device_required"])
        self.assertFalse(rows["phone-virtual-01"]["execution_eligible"])
        self.assertTrue(rows["arkan-virtual-01"]["indicator_selected"])
        self.assertEqual(result["active_software_node"]["indicator_target"], "arkan-virtual-01")
        self.assertEqual(result["active_software_node"]["display_name"], "Arkan virtual computer")
        self.assertEqual(result["active_software_node"]["indicator_state"], "NOT_PROVISIONED")
        self.assertFalse(result["active_software_node"]["physical_device_required"])
        self.assertNotIn("redmi3-01", rows)
        self.assertNotIn("realme-pending-identity", rows)
        self.assertNotIn("honda-enp1-2023", rows)
        self.assertEqual(rows["arkan-virtual-01"]["observed_state"], "NOT_PROVISIONED")
        self.assertEqual(rows["arkan-virtual-01"]["role"], "virtual_computer")
        self.assertEqual(rows["arkan-virtual-01"]["platform"], "brain-simulator")
        self.assertEqual(rows["arkan-virtual-01"]["allowed_workloads"], ["virtual_simulation"])
        self.assertFalse(rows["arkan-virtual-01"]["execution_eligible"])
        self.assertFalse(result["cloud"]["capacity_verified"])
        self.assertFalse(result["cloud"]["paid_provisioning_allowed"])


if __name__ == "__main__":
    unittest.main()
