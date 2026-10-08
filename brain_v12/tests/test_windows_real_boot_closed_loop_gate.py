import json
import os
import tempfile
import time
import unittest

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
