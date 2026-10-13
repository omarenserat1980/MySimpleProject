"""Integration regression for single-use owner approval at contract issuance."""
from __future__ import annotations

import base64
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.brain_identity import IDENTITY_SCHEMA
from brain_v12.brain.brain_leadership import BrainLeadershipStore
from brain_v12.brain.owner_cryptographic_approval import SCHEMA, approval_payload
from brain_v12.brain.windows_execution_contract_issuer import issue_from_files


class WindowsContractIssuerReplayIntegrationTests(unittest.TestCase):
    def test_same_signed_owner_challenge_cannot_issue_two_contracts(self):
        private_key = Ed25519PrivateKey.generate()
        public_key_b64 = base64.b64encode(
            private_key.public_key().public_bytes_raw()
        ).decode("ascii")
        private_key_b64 = base64.b64encode(private_key.private_bytes_raw()).decode("ascii")
        now = time.time()
        source_commit = "a" * 40
        approval = {
            "schema": SCHEMA,
            "owner_id": "owner-test",
            "challenge_id": "windows-boot-challenge-once",
            "scope": "windows-server-2025-real-boot",
            "expires_at": now + 3600,
            "source_commit": source_commit,
            "task_id": "windows-server-2025-real-boot",
            "attempt_id": "github-test-attempt-1",
        }
        approval["signature"] = base64.b64encode(
            private_key.sign(
                approval_payload(
                    approval["owner_id"],
                    approval["challenge_id"],
                    approval["scope"],
                    approval["expires_at"],
                    approval["source_commit"],
                    approval["task_id"],
                    approval["attempt_id"],
                )
            )
        ).decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = {
                "schema": IDENTITY_SCHEMA,
                "brain_id": "brain-security-test",
                "generation": 1,
                "source_commit": source_commit,
                "checkpoint_id": "SECURITY-TEST-CHECKPOINT",
            }
            checkpoint = {
                "checkpoint_id": "SECURITY-TEST-CHECKPOINT",
                "source_commit": source_commit,
                "status": "STABLE_BASELINE",
            }
            for name, payload in (
                ("identity.json", identity),
                ("checkpoint.json", checkpoint),
                ("owner-approval.json", approval),
            ):
                (root / name).write_text(json.dumps(payload), encoding="utf-8")

            # issue_from_files opens the durable store at a relative default path.
            # Isolate that path in this temporary directory so the test cannot touch
            # the developer or CI runner's real control-plane database.
            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                store = BrainLeadershipStore()
                try:
                    lease = store.acquire(
                        identity, checkpoint, "windows-real-boot-qemu", lease_seconds=3600
                    )
                finally:
                    store.close()
                (root / "lease.json").write_text(
                    json.dumps({
                        "brain_id": lease.brain_id,
                        "generation": lease.generation,
                        "lease_id": lease.lease_id,
                        "fencing_token": lease.fencing_token,
                        "holder_id": lease.holder_id,
                        "acquired_at": lease.acquired_at,
                        "expires_at": lease.expires_at,
                    }),
                    encoding="utf-8",
                )
                env = {
                    "BRAIN_HUMAN_APPROVAL_TOKEN": "test-approval-token",
                    "BRAIN_AUTHORITY_PRIVATE_KEY_B64": private_key_b64,
                }
                with patch.dict(os.environ, env, clear=False):
                    kwargs = {
                        "identity_file": str(root / "identity.json"),
                        "checkpoint_file": str(root / "checkpoint.json"),
                        "lease_file": str(root / "lease.json"),
                        "owner_approval_file": str(root / "owner-approval.json"),
                        "owner_public_key_b64": public_key_b64,
                        "output": str(root / "contract.json"),
                        "source_commit": source_commit,
                        "task_id": approval["task_id"],
                        "attempt_id": approval["attempt_id"],
                        "capability_verified": True,
                        "human_approval_token": "test-approval-token",
                    }
                    first = issue_from_files(**kwargs)
                    self.assertTrue(first["verified"])
                    self.assertTrue((root / "contract.json").is_file())

                    with self.assertRaisesRegex(RuntimeError, "OWNER_APPROVAL_REPLAY"):
                        issue_from_files(**kwargs)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
