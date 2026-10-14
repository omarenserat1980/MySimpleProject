import unittest

from brain_v12.brain.gen_challenge_registry import GENChallengeRegistry


class GENChallengeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.now = [1_800_000_000.0]
        self.registry = GENChallengeRegistry(ttl_seconds=30, clock=lambda: self.now[0])
        self.scope = {
            "issuer_id": "trusted-provider",
            "subject_id": "asic-01",
            "subject_type": "HOSTED_ASIC",
            "operation": "read_only_diagnostic",
        }

    def test_issue_returns_unpredictable_nonce_and_scoped_expiry(self):
        challenge = self.registry.issue(**self.scope)
        self.assertGreaterEqual(len(challenge.nonce), 32)
        self.assertEqual(challenge.expires_at - challenge.issued_at, 30)
        self.assertEqual(challenge.subject_id, "asic-01")

    def test_challenge_can_only_be_consumed_once(self):
        challenge = self.registry.issue(**self.scope)
        self.registry.consume(nonce=challenge.nonce, **self.scope)
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_UNKNOWN_OR_REPLAYED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_expired_challenge_rejected(self):
        challenge = self.registry.issue(**self.scope)
        self.now[0] += 31
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_UNKNOWN_OR_REPLAYED|GEN_CHALLENGE_EXPIRED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_wrong_scope_consumes_and_rejects_challenge(self):
        challenge = self.registry.issue(**self.scope)
        wrong = dict(self.scope, subject_id="other-device")
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_SCOPE_MISMATCH"):
            self.registry.consume(nonce=challenge.nonce, **wrong)
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_UNKNOWN_OR_REPLAYED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_invalid_ttl_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_TTL_INVALID"):
            GENChallengeRegistry(ttl_seconds=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
