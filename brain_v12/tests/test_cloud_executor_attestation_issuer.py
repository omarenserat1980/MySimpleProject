import base64
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.cloud_executor_attestation import verify_attestation
from brain_v12.brain.cloud_executor_attestation_issuer import create_challenge, issue_attestation, consume_issued_attestation, _connect


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
        self.hostname = "runner-test-01"

    def challenge(self, **kwargs):
        return create_challenge(expected_hostname=self.hostname, expected_architecture="x86_64", **kwargs)

    def issue(self, **kwargs):
        return issue_attestation(expected_hostname=self.hostname, expected_architecture="x86_64", **kwargs)

    def test_postgres_registry_requires_tls(self):
        with self.assertRaisesRegex(ValueError, "POSTGRES_TLS_REQUIRED"):
            _connect("postgresql://user:pass@localhost/brain")

    def test_postgres_registry_accepts_tls_mode_without_connecting(self):
        from brain_v12.brain.cloud_executor_attestation_issuer import _postgres_tls_configured
        self.assertTrue(_postgres_tls_configured("postgresql://user:pass@localhost/brain?sslmode=require"))
        self.assertTrue(_postgres_tls_configured("postgresql://user:pass@localhost/brain?sslmode=verify-full"))
        self.assertFalse(_postgres_tls_configured("postgresql://user:pass@localhost/brain?sslmode=disable"))

    def test_issues_and_verifies_single_use_challenge(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        path = Path(self.tmp.name) / "att.json"
        path.write_text(json.dumps(att))
        result = verify_attestation(str(path), self.public_b64, "cloud-test-01", now=self.now,
            replay_db_path=self.replay_db, expected_hostname=self.hostname, expected_architecture="x86_64")
        self.assertTrue(result["verified"])

    def test_issued_attestation_binds_trusted_host_and_architecture(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        self.assertEqual(att["hostname"], self.hostname)
        self.assertEqual(att["architecture"], "x86_64")
        path = Path(self.tmp.name) / "host-bound.json"
        path.write_text(json.dumps(att))
        with self.assertRaisesRegex(ValueError, "HOSTNAME_MISMATCH"):
            verify_attestation(str(path), self.public_b64, "cloud-test-01", now=self.now,
                expected_hostname="different-host", expected_architecture="x86_64")

    def test_issuer_rejects_missing_trusted_host_binding(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(TypeError, "expected_hostname"):
            issue_attestation(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)

    def test_issuer_rejects_challenge_rebound_to_another_host(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_HOST_BINDING_MISMATCH"):
            issue_attestation(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, expected_hostname="other-host", expected_architecture="x86_64",
                private_key_b64=self.private_b64, issued_at=self.now)

    def test_issuer_rejects_reused_challenge(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        args = dict(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        self.issue(**args)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_REPLAY"):
            self.issue(**args)

    def test_issuer_rejects_challenge_for_other_executor(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_EXECUTOR_MISMATCH"):
            self.issue(authenticated_executor_id="attacker", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)

    def test_issuer_rejects_expired_challenge(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with self.assertRaisesRegex(ValueError, "CHALLENGE_EXPIRED"):
            self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
                challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now + 61)

    def test_central_registry_consumes_attestation_once(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        result = consume_issued_attestation(authenticated_executor_id="cloud-test-01",
            nonce=att["nonce"], registry_db_path=self.db, now=self.now + 1)
        self.assertTrue(result["consumed"])
        with self.assertRaisesRegex(ValueError, "REPLAY_DETECTED"):
            consume_issued_attestation(authenticated_executor_id="cloud-test-01",
                nonce=att["nonce"], registry_db_path=self.db, now=self.now + 2)

    def test_central_registry_rejects_other_executor(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now)
        with self.assertRaisesRegex(ValueError, "EXECUTOR_MISMATCH"):
            consume_issued_attestation(authenticated_executor_id="attacker",
                nonce=att["nonce"], registry_db_path=self.db, now=self.now + 1)

    def test_central_registry_rejects_expired_attestation(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01", challenge_nonce=challenge["nonce"],
            challenge_db_path=self.db, private_key_b64=self.private_b64, issued_at=self.now, lifetime_seconds=10)
        with self.assertRaisesRegex(ValueError, "EXPIRED"):
            consume_issued_attestation(authenticated_executor_id="cloud-test-01",
                nonce=att["nonce"], registry_db_path=self.db, now=self.now + 11)

    def test_missing_signing_key_does_not_consume_challenge(self):
        challenge = self.challenge(authenticated_executor_id="cloud-test-01", challenge_db_path=self.db, now=self.now)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SIGNING_KEY_REQUIRED"):
                self.issue(authenticated_executor_id="cloud-test-01",
                    challenge_nonce=challenge["nonce"], challenge_db_path=self.db, issued_at=self.now)
        att = self.issue(authenticated_executor_id="cloud-test-01",
            challenge_nonce=challenge["nonce"], challenge_db_path=self.db,
            private_key_b64=self.private_b64, issued_at=self.now)
        self.assertEqual(att["nonce"], challenge["nonce"])


if __name__ == "__main__":
    unittest.main()
