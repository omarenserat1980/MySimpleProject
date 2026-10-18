from __future__ import annotations

import asyncio
import json
import os
import unittest
from types import SimpleNamespace

from brain_v12.brain.brain_mcp import build_mcp_router


class BrainMcpRouterAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_token = os.environ.get("BRAIN_MCP_TOKEN")
        self.router = build_mcp_router(None, None, None)
        self.endpoints = {
            (method, route.path): route.endpoint
            for route in self.router.routes
            for method in getattr(route, "methods", set())
        }

    def tearDown(self):
        if self.original_token is None:
            os.environ.pop("BRAIN_MCP_TOKEN", None)
        else:
            os.environ["BRAIN_MCP_TOKEN"] = self.original_token

    def call(self, method, headers):
        request = SimpleNamespace(headers=headers)
        return asyncio.run(self.endpoints[(method, "/mcp")](request))

    def test_missing_server_token_fails_closed(self):
        os.environ.pop("BRAIN_MCP_TOKEN", None)
        response = self.call("GET", {})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.body)["status"], "MCP_NOT_CONFIGURED")

    def test_missing_or_invalid_bearer_token_is_rejected(self):
        os.environ["BRAIN_MCP_TOKEN"] = "unit-test-secret"
        for headers in ({}, {"authorization": "Bearer wrong"}):
            with self.subTest(headers=headers):
                response = self.call("GET", headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers.get("www-authenticate"), "Bearer")

    def test_valid_bearer_reaches_protocol_validation(self):
        os.environ["BRAIN_MCP_TOKEN"] = "unit-test-secret"
        response = self.call("GET", {
            "authorization": "Bearer unit-test-secret",
            "MCP-Protocol-Version": "unsupported",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.body)["error"], "UNSUPPORTED_MCP_PROTOCOL_VERSION")


if __name__ == "__main__":
    unittest.main()
