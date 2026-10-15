import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID, ObjectIdentifier

from brain_phone_base.android_key_attestation import (
    ATTESTATION_EXTENSION_OID,
    AttestationError,
    verify_android_key_attestation_chain,
)


def _tlv(tag: int, value: bytes) -> bytes:
    length = len(value)
    if length < 128:
        encoded_length = bytes([length])
    else:
        raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
        encoded_length = bytes([0x80 | len(raw)]) + raw
    return bytes([tag]) + encoded_length + value


def _integer(value: int, tag: int = 0x02) -> bytes:
    raw = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return _tlv(tag, raw)


def _high_tag(number: int, value: bytes) -> bytes:
    parts = [number & 0x7F]
    number >>= 7
    while number:
        parts.insert(0, 0x80 | (number & 0x7F))
        number >>= 7
    encoded_tag = b"\xbf" + bytes(parts)
    length = len(value)
    if length < 128:
        encoded_length = bytes([length])
    else:
        raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
        encoded_length = bytes([0x80 | len(raw)]) + raw
    return encoded_tag + encoded_length + value


def _authorization_list(fields: dict[int, bytes]) -> bytes:
    return _tlv(0x30, b"".join(_high_tag(number, value) for number, value in fields.items()))


def _attestation_der(challenge: bytes, attestation_level: int = 1, keymaster_level: int = 1, locked: bool = True, boot_state: int = 0, patch_level: int = 202610) -> bytes:
    root_of_trust = _tlv(0x30, _tlv(0x04, b"boot-key") + _tlv(0x01, b"\xff" if locked else b"\x00") + _tlv(0x0A, bytes([boot_state])) + _tlv(0x04, b"boot-hash"))
    tee = _authorization_list({704: root_of_trust, 706: _tlv(0x02, (patch_level).to_bytes(3, "big")), 718: _tlv(0x02, (patch_level).to_bytes(3, "big")), 719: _tlv(0x02, (patch_level).to_bytes(3, "big"))})
    fields = b"".join([
        _integer(4), _integer(attestation_level, 0x0A), _integer(4),
        _integer(keymaster_level, 0x0A), _tlv(0x04, challenge), _tlv(0x04, b""),
        _tlv(0x30, b""), tee,
    ])
    return _tlv(0x30, fields)


class AndroidKeyAttestationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        self.challenge = b"enrollment-challenge-nonce-0123456789"
        self.root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.device_key = ec.generate_private_key(ec.SECP256R1())
        root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Attestation Root")])
        leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Attested Device Key")])
        self.root = (
            x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
            .public_key(self.root_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=2)).not_valid_after(self.now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False, key_agreement=False,
                key_cert_sign=True, crl_sign=True, encipher_only=None, decipher_only=None), critical=True)
            .sign(self.root_key, hashes.SHA256())
        )
        self.leaf = self._make_leaf(self.challenge)
        self.root_der = self.root.public_bytes(serialization.Encoding.DER)
        self.leaf_der = self.leaf.public_bytes(serialization.Encoding.DER)
        self.root_pin = hashlib.sha256(self.root_der).hexdigest()
        self.device_public_pem = self.device_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def _make_leaf(self, challenge, **attestation_options):
        leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Attested Device Key")])
        return (
            x509.CertificateBuilder().subject_name(leaf_name).issuer_name(self.root.subject)
            .public_key(self.device_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1)).not_valid_after(self.now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False, encipher_only=None, decipher_only=None), critical=True)
            .add_extension(x509.UnrecognizedExtension(ObjectIdentifier(ATTESTATION_EXTENSION_OID), _attestation_der(challenge, **attestation_options)), critical=False)
            .sign(self.root_key, hashes.SHA256())
        )

    def verify(self, **overrides):
        args = {
            "certificate_chain": [self.leaf_der, self.root_der],
            "trusted_root_sha256_fingerprints": {self.root_pin},
            "expected_attestation_challenge": self.challenge,
            "expected_device_public_key_pem": self.device_public_pem,
            "now": self.now,
        }
        args.update(overrides)
        return verify_android_key_attestation_chain(**args)

    def test_valid_pinned_chain_and_challenge_still_do_not_grant_trust(self):
        result = self.verify()
        self.assertTrue(result["certificate_chain_valid"])
        self.assertTrue(result["root_pin_valid"])
        self.assertTrue(result["attestation_challenge_matches"])
        self.assertTrue(result["attested_public_key_matches"])
        self.assertEqual(result["status"], "CHAIN_AND_CHALLENGE_VALID_POLICY_INCOMPLETE")
        self.assertFalse(result["android_key_attestation_verified"])
        self.assertFalse(result["device_identity_verified"])
        self.assertFalse(result["trusted"])
        self.assertFalse(result["active"])
        self.assertEqual(result["mining"], "DISABLED")
        self.assertEqual(result["verified_boot"]["verified_boot_state"], "VERIFIED")
        self.assertTrue(result["verified_boot"]["device_locked"])
        self.assertEqual(result["patch_levels"]["os"], 202610)


    def test_unlocked_device_fails_closed(self):
        leaf = self._make_leaf(self.challenge, locked=False)
        with self.assertRaisesRegex(AttestationError, "DEVICE_NOT_LOCKED"):
            self.verify(certificate_chain=[leaf.public_bytes(serialization.Encoding.DER), self.root_der])

    def test_non_green_boot_fails_closed(self):
        leaf = self._make_leaf(self.challenge, boot_state=2)
        with self.assertRaisesRegex(AttestationError, "VERIFIED_BOOT_NOT_GREEN"):
            self.verify(certificate_chain=[leaf.public_bytes(serialization.Encoding.DER), self.root_der])

    def test_patch_level_below_minimum_fails_closed(self):
        leaf = self._make_leaf(self.challenge, patch_level=202401)
        with self.assertRaisesRegex(AttestationError, "OS_PATCH_LEVEL_BELOW_POLICY"):
            self.verify(certificate_chain=[leaf.public_bytes(serialization.Encoding.DER), self.root_der], minimum_os_patch_level=202601)

    def test_unpinned_root_fails_closed(self):
        with self.assertRaisesRegex(AttestationError, "ROOT_CERTIFICATE_NOT_PINNED"):
            self.verify(trusted_root_sha256_fingerprints={"0" * 64})

    def test_challenge_mismatch_fails_closed(self):
        with self.assertRaisesRegex(AttestationError, "ATTESTATION_CHALLENGE_MISMATCH"):
            self.verify(expected_attestation_challenge=b"wrong-challenge")

    def test_leaf_key_mismatch_fails_closed(self):
        other = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with self.assertRaisesRegex(AttestationError, "ATTESTATION_LEAF_KEY_MISMATCH"):
            self.verify(expected_device_public_key_pem=other)

    def test_missing_attestation_extension_fails_closed(self):
        leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "No Attestation")])
        leaf = (x509.CertificateBuilder().subject_name(leaf_name).issuer_name(self.root.subject)
            .public_key(self.device_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1)).not_valid_after(self.now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False, encipher_only=None, decipher_only=None), critical=True)
            .sign(self.root_key, hashes.SHA256()))
        with self.assertRaisesRegex(AttestationError, "ANDROID_KEY_ATTESTATION_EXTENSION_MISSING"):
            self.verify(certificate_chain=[leaf.public_bytes(serialization.Encoding.DER), self.root_der])


if __name__ == "__main__":
    unittest.main()
