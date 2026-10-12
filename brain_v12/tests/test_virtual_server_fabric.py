import unittest
from unittest.mock import patch

from brain_v12.virtual_hardware.server_fabric import (
    HOST_OBSERVED, HostCapacity, SERVER_PROFILES, admit_server_workload,
    discover_backends, get_server_profile, list_server_profiles,
    observe_host_capacity, validate_server_release,
)


class VirtualServerFabricTests(unittest.TestCase):
    def test_profiles_are_deterministic_and_simulation_first(self):
        first = list_server_profiles()
        second = list_server_profiles()
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 10)
        self.assertTrue(all(p["fidelity"] == "SIMULATED" for p in first))
        self.assertTrue(all(p["validation"]["ok"] for p in first))
        self.assertTrue(all(not p["external_network_default"] for p in first))

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SERVER_PROFILE"):
            get_server_profile("made-up-server")

    def test_windows_server_release_identifier_does_not_fake_media_or_boot(self):
        result = validate_server_release("Windows Server", "2025")
        self.assertTrue(result["ok"])
        self.assertFalse(result["media_verified"])
        self.assertFalse(result["boot_verified"])
        self.assertEqual(validate_server_release("Windows Server", "2023")["status"],
                         "UNVERIFIED_WINDOWS_SERVER_RELEASE")

    def test_host_observation_has_host_provenance_and_no_side_effects(self):
        observed = observe_host_capacity(".")
        self.assertEqual(observed.provenance, HOST_OBSERVED)
        self.assertGreaterEqual(observed.logical_cpus, 1)
        self.assertIsNotNone(observed.available_disk_bytes)

    def test_admission_rejects_unknown_host_capacity(self):
        host = HostCapacity(4, None, None, "Linux", "x86_64")
        result = admit_server_workload(SERVER_PROFILES[0], host)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "HOST_CAPACITY_UNKNOWN")

    def test_admission_rejects_simulated_host_measurements(self):
        host = HostCapacity(4, 8192, 100 * 1024**3, "Linux", "x86_64", "SIMULATED")
        result = admit_server_workload(SERVER_PROFILES[0], host)
        self.assertEqual(result["status"], "HOST_CAPACITY_NOT_OBSERVED")

    def test_admission_rejects_insufficient_memory_disk_and_cpu(self):
        profile = get_server_profile("brain-server-database-v1")
        host = HostCapacity(1, 512, 2 * 1024**3, "Android", "arm", HOST_OBSERVED)
        result = admit_server_workload(profile, host)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "INSUFFICIENT_HOST_CAPACITY")
        self.assertFalse(result["resources_reserved"])
        self.assertFalse(result["vm_started"])

    def test_admission_passes_capacity_check_without_allocating_resources(self):
        profile = get_server_profile("brain-server-web-v1")
        host = HostCapacity(8, 8192, 100 * 1024**3, "Linux", "x86_64", HOST_OBSERVED)
        result = admit_server_workload(profile, host)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ADMITTED_FOR_PLANNING")
        self.assertFalse(result["resources_reserved"])
        self.assertFalse(result["vm_started"])

    def test_invalid_reserve_and_cpu_budget_are_rejected(self):
        profile = get_server_profile("brain-server-small-v1")
        host = HostCapacity(8, 8192, 100 * 1024**3, "Linux", "x86_64")
        self.assertEqual(admit_server_workload(profile, host, memory_reserve_mib=-1)["status"],
                         "INVALID_RESOURCE_RESERVE")
        self.assertEqual(admit_server_workload(profile, host, max_cpu_fraction=2)["status"],
                         "INVALID_CPU_BUDGET")

    def test_backend_discovery_never_claims_provisioning(self):
        result = discover_backends()
        self.assertFalse(result["provisioning_performed"])
        self.assertFalse(result["external_network_enabled"])
        self.assertTrue(result["backends"][0]["available"])
        self.assertEqual(result["backends"][0]["mode"], "SIMULATED")


if __name__ == "__main__":
    unittest.main()
