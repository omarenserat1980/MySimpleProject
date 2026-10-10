import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.cloud_executor_attestation import verify_attestation
from brain_v12.brain.cloud_executor_attestation_issuer import create_challenge, issue_attestation


class CloudExecutorAttestationIssuerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "challenges.sqlite3")
        self.replay_db = str(Path(self.tmp.name) / "consumed.sqlite3")
        self.private = Ed25519PrivateKey.generate()
        self.private_b64 = base64.b64encode(self.private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )).decode()
        self.public_b64 = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )).decode()
        self.now = 1_800_000_000

    def test_issues_and_verifies_single_use_challenge(self):
        challenge = create_challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = issue_attestation(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        path = Path(self.tmp.name) / "att.json"
        path.write_text(json.dumps(att))
        result = verify_attestation(str(path), self.public_b64, "cloud-test-01", now=self.now,
            replay_db_path=self.replay_db)
        self.assertTrue(result["verified"])

    def test_issuer_rejects_reused_challenge(self):
        challenge = create_challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        args = dict(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        issue_attestation(**args)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_REPLAY"):
            issue_attestation(**args)

    def test_issuer_rejects_challenge_for_other_executor(self):
        challenge = create_challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_EXECUTOR_MISMATCH"):
            issue_attestation(authenticated_executor_id="attacker", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)

    def test_issuer_rejects_expired_challenge(self):
        challenge = create_challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_EXPIRED"):
            issue_attestation(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now + 61)


if __name__ == "__main__":
    unittest.main()
