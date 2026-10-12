import unittest

from brain_v12.tools.arkan_windows_server_2025_preflight import (
    ARKAN_ID, evaluate_readiness, read_memory_mib,
)


def ready_facts():
    return {
        "canonical_id": ARKAN_ID,
        "os": "Linux",
        "arch": "x86_64",
        "cpu_cores": 8,
        "total_memory_mib": 8192,
        "available_memory_mib": 6144,
        "free_disk_gib": 80,
        "kvm_read_write": True,
        "tools": {
            "qemu-system-x86_64": True,
            "qemu-img": True,
            "xorriso": True,
            "wimlib-imagex": True,
            "mcopy": True,
            "fat_mkfs": True,
        },
        "ovmf_readable": True,
        "contract_verified": True,
    }


class ArkanWindowsServer2025PreflightTests(unittest.TestCase):
    def test_ready_host_is_only_authorized_for_attempt_not_claimed_booted(self):
        result = evaluate_readiness(ready_facts())
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "READY_FOR_AUTHORIZED_REAL_BOOT")
        self.assertEqual(result["installation_status"], "NOT_STARTED")
        self.assertEqual(result["boot_status"], "NOT_VERIFIED")
        self.assertFalse(result["windows_boot_verified"])
        self.assertFalse(result["side_effects_performed"])

    def test_simulator_identity_cannot_replace_real_kvm_substrate(self):
        facts = ready_facts()
        facts["kvm_read_write"] = False
        facts["tools"]["qemu-system-x86_64"] = False
        result = evaluate_readiness(facts)
        self.assertFalse(result["ready"])
        self.assertIn("KVM_DEVICE_NOT_READY", result["blockers"])
        self.assertIn("QEMU_NOT_READY", result["blockers"])
        self.assertFalse(result["windows_boot_verified"])

    def test_insufficient_memory_or_disk_blocks_before_media_download(self):
        facts = ready_facts()
        facts["total_memory_mib"] = 3584
        facts["available_memory_mib"] = 1200
        facts["free_disk_gib"] = 10
        result = evaluate_readiness(facts)
        self.assertFalse(result["ready"])
        self.assertIn("TOTAL_MEMORY_NOT_READY", result["blockers"])
        self.assertIn("AVAILABLE_MEMORY_NOT_READY", result["blockers"])
        self.assertIn("FREE_DISK_NOT_READY", result["blockers"])

    def test_wrong_identity_or_unverified_contract_fails_closed(self):
        facts = ready_facts()
        facts["canonical_id"] = "arkan-host-asus-vivobook"
        facts["contract_verified"] = False
        result = evaluate_readiness(facts)
        self.assertFalse(result["ready"])
        self.assertIn("CANONICAL_ARKAN_IDENTITY_NOT_READY", result["blockers"])
        self.assertIn("SIGNED_CONTRACT_GATE_NOT_READY", result["blockers"])

    def test_missing_media_tools_blocks(self):
        facts = ready_facts()
        facts["tools"]["wimlib-imagex"] = False
        facts["tools"]["fat_mkfs"] = False
        result = evaluate_readiness(facts)
        self.assertFalse(result["ready"])
        self.assertIn("MEDIA_TOOLS_NOT_READY", result["blockers"])
        self.assertIn("FAT_TOOLS_NOT_READY", result["blockers"])

    def test_memory_probe_fails_closed_for_missing_or_malformed_file(self):
        total, available = read_memory_mib("/definitely/missing/meminfo")
        self.assertEqual((total, available), (0, 0))


if __name__ == "__main__":
    unittest.main()
