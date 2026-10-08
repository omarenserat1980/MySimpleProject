import unittest

from brain_v12.brain.cloud_machine_contract import (
    CloudMachineContract,
    accept,
    REQUIRED_SCHEMA,
)


class CloudMachineContractTests(unittest.TestCase):
    def valid(self):
        return CloudMachineContract(
            schema=REQUIRED_SCHEMA,
            machine_id="cloud-test-01",
            architecture="x86_64",
            vcpu=4,
            ram_mb=8192,
            storage_gb=120,
            network=True,
            virtualization=True,
            uefi=True,
            qemu=True,
            ovmf=True,
            evidence_id="cloud-evidence-test",
        )

    def test_accepts_valid_machine(self):
        r = accept(self.valid())
        self.assertTrue(r["accepted"])
        self.assertEqual(r["status"], "CLOUD_MACHINE_ACCEPTED")

    def test_rejects_missing_virtualization(self):
        c = self.valid()
        c = CloudMachineContract(**{**c.as_dict(), "virtualization": False})
        r = accept(c)
        self.assertFalse(r["accepted"])
        self.assertIn("VIRTUALIZATION_UNAVAILABLE", r["failures"])

    def test_rejects_insufficient_memory(self):
        c = self.valid()
        c = CloudMachineContract(**{**c.as_dict(), "ram_mb": 2048})
        r = accept(c)
        self.assertFalse(r["accepted"])
        self.assertIn("RAM_INSUFFICIENT", r["failures"])


if __name__ == "__main__":
    unittest.main()
