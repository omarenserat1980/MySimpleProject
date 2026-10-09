import base64
import json
import os
import tempfile
import time
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.authority_signature import ALGORITHM, sign_contract
from brain_v12.brain.windows_real_boot_closed_loop_gate import load_and_verify


class WindowsClosedLoopGateTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key_b64 = base64.b64encode(
            self.private_key.public_key().public_bytes_raw()
        ).decode()
        self.old_public_key = os.environ.get("BRAIN_AUTHORITY_PUBLIC_KEY_B64")
        os.environ["BRAIN_AUTHORITY_PUBLIC_KEY_B64"] = self.public_key_b64

    def tearDown(self):
        if self.old_public_key is None:
            os.environ.pop("BRAIN_AUTHORITY_PUBLIC_KEY_B64", None)
        else:
            os.environ["BRAIN_AUTHORITY_PUBLIC_KEY_B64"] = self.old_public_key

    def contract(self):
        value = {
            "schema": "brain.windows-execution-contract.v1",
            "status": "VERIFIED",
            "capability": "windows-server-2025-real-boot",
            "executor": "windows-real-boot-qemu",
            "brain_id": "brain-test",
            "generation": 7,
            "fencing_token": 19,
            "lease_id": "lease-19",
            "holder_id": "cloud-qemu-01",
            "task_id": "windows-real-boot",
            "attempt_id": "attempt-abc",
            "source_commit": "a" * 40,
            "authority_policy_version": "authority-policy-v1",
            "authority_decision": "AUTHORIZED",
            "expires_at": time.time() + 300,
            "authority_signature_algorithm": ALGORITHM,
        }
        private_key_b64 = base64.b64encode(self.private_key.private_bytes_raw()).decode()
        value["authority_signature"] = sign_contract(value, private_key_b64)
        return value

    def write(self, value):
        f = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        json.dump(value, f)
        f.close()
        self.addCleanup(lambda: os.unlink(f.name))
        return f.name

    def test_accepts_current_contract(self):
        old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "a" * 40
        try:
            result = load_and_verify(self.write(self.contract()))
            self.assertTrue(result["verified"])
            self.assertEqual(result["contract"]["fencing_token"], 19)
        finally:
            if old is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = old

    def test_rejects_expired_contract(self):
        value = self.contract()
        value["expires_at"] = time.time() - 1
        with self.assertRaisesRegex(RuntimeError, "EXPIRED"):
            load_and_verify(self.write(value))

    def test_rejects_stale_source_commit(self):
        old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "b" * 40
        try:
            with self.assertRaisesRegex(RuntimeError, "SOURCE_COMMIT_MISMATCH"):
                load_and_verify(self.write(self.contract()))
        finally:
            if old is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = old

    def test_rejects_modified_contract_with_stale_signature(self):
        value = self.contract()
        value.pop("fencing_token")
        with self.assertRaisesRegex(RuntimeError, "AUTHORITY_SIGNATURE_INVALID"):
            load_and_verify(self.write(value))


if __name__ == "__main__":
    unittest.main()
