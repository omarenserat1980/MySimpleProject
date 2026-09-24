import os
import unittest

from fastapi import HTTPException
from starlette.requests import Request

from brain_v12.brain.control_auth import require_control_key


def make_request(key=""):
    headers = []
    if key:
        headers.append((b"x-brain-control-key", key.encode()))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


class ControlAuthTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BRAIN_CONTROL_KEY")

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BRAIN_CONTROL_KEY", None)
        else:
            os.environ["BRAIN_CONTROL_KEY"] = self.previous

    def test_missing_configuration_is_denied(self):
        os.environ.pop("BRAIN_CONTROL_KEY", None)
        with self.assertRaises(HTTPException) as ctx:
            require_control_key(make_request("anything"))
        self.assertEqual(ctx.exception.status_code, 503)

    def test_wrong_key_is_denied(self):
        os.environ["BRAIN_CONTROL_KEY"] = "expected-secret"
        with self.assertRaises(HTTPException) as ctx:
            require_control_key(make_request("wrong-secret"))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_correct_key_is_allowed(self):
        os.environ["BRAIN_CONTROL_KEY"] = "expected-secret"
        require_control_key(make_request("expected-secret"))


if __name__ == "__main__":
    unittest.main()
