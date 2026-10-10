import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from brain_v12.brain.cloud_executor_attestation_api import (
    ConsumeRequest, ExecutorRequest, IssueRequest, attestation_challenge,
    attestation_consume, attestation_issue,
)


class CloudExecutorAttestationApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "registry.sqlite3")
        private = Ed25519PrivateKey.generate()
        self.private_b64 = base64.b64encode(private.private_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption())).decode()
        self.token = "test-only-enrollment-token"
        self.env = patch.dict("os.environ", {
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_DB": self.db,
            "BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON": json.dumps({"cloud-test-01": hashlib.sha256(self.token.encode()).hexdigest()}),
            "BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64": self.private_b64,
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_authenticated_flow_challenge_issue_consume(self):
        challenge = attestation_challenge(ExecutorRequest(executor_id="cloud-test-01"), self.token)
        att = attestation_issue(IssueRequest(executor_id="cloud-test-01", nonce=challenge["nonce"]), self.token)
        result = attestation_consume(ConsumeRequest(executor_id="cloud-test-01", nonce=att["nonce"]), self.token)
        self.assertTrue(result["consumed"])

    def test_rejects_bad_executor_token(self):
        with self.assertRaisesRegex(HTTPException, ".*"):
            attestation_challenge(ExecutorRequest(executor_id="cloud-test-01"), "wrong-token")

    def test_rejects_unenrolled_executor(self):
        with self.assertRaises(HTTPException) as raised:
            attestation_challenge(ExecutorRequest(executor_id="attacker"), self.token)
        self.assertEqual(raised.exception.status_code, 403)

    def test_rejects_second_consume(self):
        challenge = attestation_challenge(ExecutorRequest(executor_id="cloud-test-01"), self.token)
        att = attestation_issue(IssueRequest(executor_id="cloud-test-01", nonce=challenge["nonce"]), self.token)
        body = ConsumeRequest(executor_id="cloud-test-01", nonce=att["nonce"])
        attestation_consume(body, self.token)
        with self.assertRaises(HTTPException) as raised:
            attestation_consume(body, self.token)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
