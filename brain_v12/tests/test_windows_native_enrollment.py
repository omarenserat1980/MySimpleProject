import hashlib
import hmac
import unittest

from brain_v12.brain.windows_native_enrollment import (
    WINDOWS_NATIVE_ATTESTATION_V1,
    WindowsNativeEnrollment,
)


TOKEN = "test-only-signing-token"


def signed(enrollment):
    payload = enrollment.attestation_payload()
    import json
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hmac.new(TOKEN.encode(), canonical, hashlib.sha256).hexdigest()


class WindowsNativeEnrollmentTests(unittest.TestCase):
    def enrollment(self, **overrides):
        values = dict(
            enrollment_id="enroll-01",
            executor_id="windows-native-vivobook-01",
            server_id="vivobook-01",
            brain_id="brain-primary",
            brain_generation=8,
            network_generation=7,
            challenge="challenge-123",
            platform="Windows Server 2025",
            architecture="x86_64",
        )
        values.update(overrides)
        return WindowsNativeEnrollment(**values)

    def test_valid_signature_verifies(self):
        enrollment = self.enrollment()
        result = enrollment.verify(signed(enrollment), TOKEN)
        self.assertTrue(result["verified"])
        self.assertEqual(WINDOWS_NATIVE_ATTESTATION_V1, result["schema"])
        self.assertTrue(result["attestation_digest"])

    def test_wrong_signature_fails(self):
        enrollment = self.enrollment()
        result = enrollment.verify("00" * 32, TOKEN)
        self.assertFalse(result["verified"])

    def test_wrong_token_fails(self):
        enrollment = self.enrollment()
        result = enrollment.verify(signed(enrollment), "wrong-token")
        self.assertFalse(result["verified"])

    def test_tampered_network_generation_fails(self):
        enrollment = self.enrollment(network_generation=7)
        signature = signed(enrollment)
        tampered = self.enrollment(network_generation=8)
        self.assertFalse(tampered.verify(signature, TOKEN)["verified"])

    def test_invalid_generation_rejected(self):
        with self.assertRaisesRegex(ValueError, "brain_generation"):
            self.enrollment(brain_generation=0).validate()


if __name__ == "__main__":
    unittest.main()
