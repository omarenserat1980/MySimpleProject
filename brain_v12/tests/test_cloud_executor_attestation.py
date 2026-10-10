import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.cloud_executor_attestation import (
    AUDIENCE, SCHEMA, signing_payload, verify_attestation, verify_from_environment,
)


class _Response:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return b'{"consumed": true}'


class CloudExecutorAttestationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key_b64 = base64.b64encode(self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode()
        self.now = 1_800_000_000
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.replay_db = str(Path(self.tmp.name) / "used-nonces.sqlite3")
        self.document = {
            "schema": SCHEMA, "executor_id": "cloud-test-01", "audience": AUDIENCE,
            "issued_at": self.now - 5, "expires_at": self.now + 300,
            "nonce": "nonce-1234567890",
        }

    def write_signed(self, document=None):
        doc = dict(self.document if document is None else document)
        doc["signature"] = base64.b64encode(self.private_key.sign(signing_payload(doc))).decode()
        path = Path(self.tmp.name) / f'attestation-{len(list(Path(self.tmp.name).glob("attestation-*.json")))}.json'
        path.write_text(json.dumps(doc), encoding="utf-8")
        return str(path)

    def verify(self, path, **kwargs):
        return verify_attestation(path, self.public_key_b64,
            kwargs.pop("expected_executor_id", "cloud-test-01"),
            now=kwargs.pop("now", self.now), **kwargs)

    def test_accepts_valid_signed_attestation(self):
        self.assertTrue(self.verify(self.write_signed())["verified"])

    def test_rejects_modified_payload(self):
        path = self.write_signed()
        doc = json.loads(Path(path).read_text())
        doc["nonce"] = "nonce-abcdefghijklmnop"
        Path(path).write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
            self.verify(path)

    def test_rejects_wrong_trust_key(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
            verify_attestation(self.write_signed(), base64.b64encode(other).decode(),
                "cloud-test-01", now=self.now)

    def test_rejects_expired_attestation(self):
        with self.assertRaisesRegex(ValueError, "EXPIRED"):
            self.verify(self.write_signed(dict(self.document, expires_at=self.now - 1)))

    def test_rejects_wrong_audience(self):
        with self.assertRaisesRegex(ValueError, "AUDIENCE_MISMATCH"):
            self.verify(self.write_signed(dict(self.document, audience="other-service")))

    def test_rejects_overlong_validity(self):
        with self.assertRaisesRegex(ValueError, "VALIDITY_INVALID"):
            self.verify(self.write_signed(dict(self.document, expires_at=self.now + 5000)))

    def test_rejects_missing_trust_key(self):
        with self.assertRaisesRegex(ValueError, "TRUST_KEY_REQUIRED"):
            verify_attestation(self.write_signed(), "", "cloud-test-01", now=self.now)

    def test_rejects_reuse_of_consumed_nonce(self):
        path = self.write_signed()
        self.verify(path, replay_db_path=self.replay_db)
        with self.assertRaisesRegex(ValueError, "REPLAY_DETECTED"):
            self.verify(path, replay_db_path=self.replay_db)

    def test_replay_ledger_is_shared_across_attestation_files(self):
        self.verify(self.write_signed(), replay_db_path=self.replay_db)
        with self.assertRaisesRegex(ValueError, "REPLAY_DETECTED"):
            self.verify(self.write_signed(), replay_db_path=self.replay_db)

    def test_rejects_replay_store_symlink(self):
        real_db = str(Path(self.tmp.name) / "real.sqlite3")
        self.verify(self.write_signed(), replay_db_path=real_db)
        link = str(Path(self.tmp.name) / "link.sqlite3")
        Path(link).symlink_to(real_db)
        fresh = dict(self.document, nonce="nonce-abcdefghijklmnop")
        with self.assertRaisesRegex(ValueError, "SYMLINK_REJECTED"):
            self.verify(self.write_signed(fresh), replay_db_path=link)

    def test_environment_verifier_requires_central_registry(self):
        path = self.write_signed()
        with patch.dict(os.environ, {
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE": path,
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64": self.public_key_b64,
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL": "",
            "BRAIN_CLOUD_EXECUTOR_TOKEN": "",
        }):
            with self.assertRaisesRegex(ValueError, "CENTRAL_REGISTRY_CONFIGURATION_REQUIRED"):
                verify_from_environment("cloud-test-01", now=self.now)

    def test_environment_verifier_requires_https(self):
        path = self.write_signed()
        with patch.dict(os.environ, {
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE": path,
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64": self.public_key_b64,
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL": "http://brain.example",
            "BRAIN_CLOUD_EXECUTOR_TOKEN": "test-token",
        }):
            with self.assertRaisesRegex(ValueError, "REGISTRY_HTTPS_REQUIRED"):
                verify_from_environment("cloud-test-01", now=self.now)

    def test_environment_verifier_consumes_nonce_at_central_registry(self):
        path = self.write_signed()
        with patch.dict(os.environ, {
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE": path,
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64": self.public_key_b64,
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL": "https://brain.example",
            "BRAIN_CLOUD_EXECUTOR_TOKEN": "test-token",
        }), patch("brain_v12.brain.cloud_executor_attestation.urllib.request.urlopen", return_value=_Response()) as opened:
            result = verify_from_environment("cloud-test-01", now=self.now)
        self.assertTrue(result["verified"])
        self.assertIn("/api/cloud-executor/attestation/consume", opened.call_args.args[0].full_url)


if __name__ == "__main__":
    unittest.main()
