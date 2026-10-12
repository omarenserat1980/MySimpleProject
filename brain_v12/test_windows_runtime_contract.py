import unittest

from brain_v12.brain.windows_runtime_contract import WindowsRuntimeContract


def evidence():
    return {
        "status": "WINDOWS_BOOT_VERIFIED",
        "guest": {
            "os": "Windows Server 2025",
            "architecture": "x86_64",
            "boot_verified": True,
        },
        "network": {"adapter_up": True, "internet_443": True},
        "storage": {"filesystem": "NTFS", "size_bytes": 64 * 1024**3},
    }


class WindowsRuntimeContractTests(unittest.TestCase):
    def test_accepts_complete_evidence(self):
        ok, reasons = WindowsRuntimeContract().validate(evidence())
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_rejects_wrong_os(self):
        e = evidence()
        e["guest"]["os"] = "Windows Server 2022"
        ok, reasons = WindowsRuntimeContract().validate(e)
        self.assertFalse(ok)
        self.assertIn("GUEST_OS_NOT_WINDOWS_SERVER_2025", reasons)

    def test_rejects_missing_network(self):
        e = evidence()
        e["network"]["internet_443"] = False
        ok, reasons = WindowsRuntimeContract().validate(e)
        self.assertFalse(ok)
        self.assertIn("HTTPS_443_NOT_REACHABLE", reasons)


if __name__ == "__main__":
    unittest.main()
