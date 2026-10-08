import unittest
from brain_v12.brain.brain_identity import IDENTITY_SCHEMA, require_newer_generation, validate_identity

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

    def test_old_generation(self):
        with self.assertRaisesRegex(RuntimeError, "BRAIN_IDENTITY_GENERATION_NOT_NEWER"):
            require_newer_generation(identity(2), 2)

    def test_new_generation(self):
        self.assertEqual(require_newer_generation(identity(3), 2)["generation"], 3)

if __name__ == "__main__":
    unittest.main()
