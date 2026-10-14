import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.gen_challenge_sqlite import GENChallengeRegistry


class GENChallengeSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "challenges.sqlite3")
        self.now = [1_800_000_000.0]
        self.registry = GENChallengeRegistry(self.db_path, ttl_seconds=30, clock=lambda: self.now[0])
        self.scope = {
            "issuer_id": "trusted-provider",
            "subject_id": "asic-01",
            "subject_type": "HOSTED_ASIC",
            "operation": "read_only_diagnostic",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_challenge_survives_registry_recreation(self):
        challenge = self.registry.issue(**self.scope)
        restarted = GENChallengeRegistry(self.db_path, ttl_seconds=30, clock=lambda: self.now[0])
        consumed = restarted.consume(nonce=challenge.nonce, **self.scope)
        self.assertEqual(consumed.nonce, challenge.nonce)

    def test_nonce_replay_rejected_after_consumption(self):
        challenge = self.registry.issue(**self.scope)
        self.registry.consume(nonce=challenge.nonce, **self.scope)
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_UNKNOWN_OR_REPLAYED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_expired_challenge_rejected(self):
        challenge = self.registry.issue(**self.scope)
        self.now[0] += 31
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_EXPIRED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_scope_mismatch_consumes_challenge(self):
        challenge = self.registry.issue(**self.scope)
        wrong = dict(self.scope, subject_id="other-device")
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_SCOPE_MISMATCH"):
            self.registry.consume(nonce=challenge.nonce, **wrong)
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_UNKNOWN_OR_REPLAYED"):
            self.registry.consume(nonce=challenge.nonce, **self.scope)

    def test_memory_database_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "GEN_CHALLENGE_DATABASE_MUST_BE_PERSISTENT"):
            GENChallengeRegistry(":memory:")


if __name__ == "__main__":
    unittest.main(verbosity=2)
