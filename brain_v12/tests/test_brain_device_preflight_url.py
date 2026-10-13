import unittest

from brain_v12.tools.brain_device_preflight import validate_brain_url


class BrainDevicePreflightURLTests(unittest.TestCase):
    def test_default_loopback_http_is_allowed(self):
        self.assertTrue(validate_brain_url("http://127.0.0.1:8012"))
        self.assertTrue(validate_brain_url("http://localhost:8012"))
        self.assertTrue(validate_brain_url("http://[::1]:8012"))

    def test_remote_https_is_allowed(self):
        self.assertTrue(validate_brain_url("https://brain.example/api"))

    def test_lookalike_loopback_hosts_are_rejected(self):
        self.assertFalse(validate_brain_url("http://127.0.0.1.attacker.example"))
        self.assertFalse(validate_brain_url("http://localhost.attacker.example"))

    def test_remote_http_and_embedded_credentials_are_rejected(self):
        self.assertFalse(validate_brain_url("http://brain.example"))
        self.assertFalse(validate_brain_url("https://user:secret@brain.example"))

    def test_malformed_ports_and_fragments_are_rejected(self):
        self.assertFalse(validate_brain_url("http://localhost:99999"))
        self.assertFalse(validate_brain_url("https://brain.example/#fragment"))


if __name__ == "__main__":
    unittest.main()
