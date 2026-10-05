import unittest

from brain_v12.brain.secret_bootstrapper import SecretBootstrapper


class SecretBootstrapperTests(unittest.TestCase):
    def test_creates_missing_secret_without_exposing_value(self):
        store = {}
        broker = SecretBootstrapper(store)
        result = broker.ensure(["BRAIN_CONTROL_TOKEN"])

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].created)
        self.assertTrue(store["BRAIN_CONTROL_TOKEN"])
        self.assertEqual(len(result[0].fingerprint), 12)

    def test_is_idempotent(self):
        store = {}
        bootstrapper = SecretBootstrapper(store)
        first = bootstrapper.ensure(["BRAIN_CONTROL_TOKEN"])[0]
        value = store["BRAIN_CONTROL_TOKEN"]
        second = bootstrapper.ensure(["BRAIN_CONTROL_TOKEN"])[0]

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(value, store["BRAIN_CONTROL_TOKEN"])
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            SecretBootstrapper({}).ensure(["bad-name"])


if __name__ == "__main__":
    unittest.main()
