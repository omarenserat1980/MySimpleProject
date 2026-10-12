import unittest
from brain_v12.brain.brain_identity import IDENTITY_SCHEMA, require_checkpoint_identity, require_newer_generation, validate_identity

def identity(generation=2):
    return {"schema": IDENTITY_SCHEMA, "brain_id": "brain-primary", "generation": generation,
            "source_commit": "a" * 40, "checkpoint_id": "BRAIN-GOLDEN-01"}

class BrainIdentityTests(unittest.TestCase):
    def test_valid_identity(self):
        self.assertTrue(validate_identity(identity())["verified"])

    def test_missing_identity(self):
        with self.assertRaisesRegex(ValueError, "BRAIN_IDENTITY_ID_REQUIRED"):
            validate_identity(identity() | {"brain_id": ""})

    def test_invalid_commit(self):
        with self.assertRaisesRegex(ValueError, "BRAIN_IDENTITY_SOURCE_COMMIT_INVALID"):
            validate_identity(identity() | {"source_commit": "bad"})

    def test_checkpoint_binding(self):
        self.assertTrue(require_checkpoint_identity(identity(), checkpoint())["verified"])

    def test_checkpoint_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, "BRAIN_IDENTITY_CHECKPOINT_MISMATCH"):
            require_checkpoint_identity(identity(), checkpoint() | {"checkpoint_id": "OTHER"})

    def test_source_commit_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, "BRAIN_IDENTITY_SOURCE_COMMIT_MISMATCH"):
            require_checkpoint_identity(identity(), checkpoint() | {"source_commit": "b" * 40})

    def test_old_generation(self):
        with self.assertRaisesRegex(RuntimeError, "BRAIN_IDENTITY_GENERATION_NOT_NEWER"):
            require_newer_generation(identity(2), 2)

    def test_new_generation(self):
        self.assertEqual(require_newer_generation(identity(3), 2)["generation"], 3)

def checkpoint():
    return {"checkpoint_id": "BRAIN-GOLDEN-01", "source_commit": "a" * 40, "status": "STABLE_BASELINE"}

if __name__ == "__main__":
    unittest.main()
