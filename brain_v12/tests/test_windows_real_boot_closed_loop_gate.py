import base64
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_v12.brain.authority_signature import sign_contract

from brain_v12.brain.windows_real_boot_closed_loop_gate import load_and_verify


def contract():
    return {
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
    }


class WindowsClosedLoopGateTests(unittest.TestCase):
    def setUp(self):
        self._old_keys = {
            name: os.environ.get(name)
            for name in ("BRAIN_AUTHORITY_PRIVATE_KEY_B64", "BRAIN_AUTHORITY_PUBLIC_KEY_B64")
        }
        key = Ed25519PrivateKey.generate()
        os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"] = base64.b64encode(key.private_bytes_raw()).decode()
        os.environ["BRAIN_AUTHORITY_PUBLIC_KEY_B64"] = base64.b64encode(key.public_key().public_bytes_raw()).decode()

    def tearDown(self):
        for name, value in self._old_keys.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def write(self, value):
        value["authority_signature_algorithm"] = "Ed25519"
        value["authority_signature"] = sign_contract(value)
        f = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        json.dump(value, f)
        f.close()
        self.addCleanup(lambda: os.unlink(f.name))
        return f.name

    def test_default_contract_path_matches_issuer_output(self):
        old = os.environ.pop("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE", None)
        seen = []
        try:
            def record_missing(path):
                seen.append(str(path))
                return False
            with patch.object(Path, "is_file", record_missing):
                with self.assertRaisesRegex(RuntimeError, "WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED"):
                    load_and_verify()
            self.assertEqual(seen, ["/run/brain/windows-execution-contract.json"])
        finally:
            if old is not None:
                os.environ["BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE"] = old

    def test_accepts_current_contract(self):
        old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "a" * 40
        try:
            r = load_and_verify(self.write(contract()))
            self.assertTrue(r["verified"])
            self.assertEqual(r["contract"]["fencing_token"], 19)
        finally:
            if old is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = old

    def test_rejects_expired_contract(self):
        c = contract()
        c["expires_at"] = time.time() - 1
        with self.assertRaisesRegex(RuntimeError, "EXPIRED"):
            load_and_verify(self.write(c))

    def test_rejects_stale_source_commit(self):
        old = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "b" * 40
        try:
            with self.assertRaisesRegex(RuntimeError, "SOURCE_COMMIT_MISMATCH"):
                load_and_verify(self.write(contract()))
        finally:
            if old is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = old

    def test_requires_fencing(self):
        c = contract()
        c.pop("fencing_token")
        with self.assertRaisesRegex(RuntimeError, "FENCING_TOKEN_REQUIRED"):
            load_and_verify(self.write(c))


if __name__ == "__main__":
    unittest.main()
