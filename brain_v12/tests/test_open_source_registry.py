import unittest
from unittest.mock import Mock, patch

import httpx

from brain_v12.brain.open_source_registry import (
    OPEN_SOURCE_SPDX_IDS,
    OpenSourceToolRegistry,
)


def repo(name="owner/tool", license_id="MIT", **extra):
    item = {
        "full_name": name,
        "name": name.split("/")[-1],
        "html_url": "https://github.com/" + name,
        "description": "Example tool",
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 123,
        "license": {"spdx_id": license_id} if license_id else None,
        "topics": ["automation"],
        "updated_at": "2026-01-01T00:00:00Z",
        "archived": False,
        "fork": False,
    }
    item.update(extra)
    return item


class OpenSourceToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = OpenSourceToolRegistry(ttl_seconds=300)

    @patch("brain_v12.brain.open_source_registry.httpx.get")
    def test_returns_only_recognized_open_source_licenses(self, get):
        response = Mock()
        response.json.return_value = {
            "items": [
                repo("owner/mit-tool", "MIT"),
                repo("owner/no-license", "NOASSERTION"),
                repo("owner/proprietary", None),
            ]
        }
        response.raise_for_status.return_value = None
        get.return_value = response

        result = self.registry.search("automation", limit=10)

        self.assertTrue(result["ok"])
        self.assertEqual([item["full_name"] for item in result["tools"]], ["owner/mit-tool"])
        self.assertEqual(result["tools"][0]["status"], "DISCOVERED_NOT_INSTALLED")
        self.assertFalse(result["tools"][0]["executable"])
        self.assertTrue(result["tools"][0]["security_review_required"])

    @patch("brain_v12.brain.open_source_registry.httpx.get")
    def test_caches_successful_search(self, get):
        response = Mock()
        response.json.return_value = {"items": [repo()]}
        response.raise_for_status.return_value = None
        get.return_value = response

        first = self.registry.search("automation")
        second = self.registry.search("automation")

        self.assertTrue(first["ok"])
        self.assertTrue(second["cached"])
        get.assert_called_once()

    @patch("brain_v12.brain.open_source_registry.httpx.get")
    def test_rate_limit_is_reported_without_exception_leak(self, get):
        response = Mock()
        response.status_code = 429
        request = httpx.Request("GET", "https://api.github.com/search/repositories")
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=request, response=response
        )
        get.return_value = response

        result = self.registry.search("automation")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "RATE_LIMITED")
        self.assertEqual(result["tools"], [])

    def test_invalid_language_filter_is_rejected(self):
        result = self.registry.search("automation", language="Python && delete")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "INVALID_LANGUAGE_FILTER")

    def test_status_disables_auto_install_and_execution(self):
        self.assertGreater(len(OPEN_SOURCE_SPDX_IDS), 10)
        status = self.registry.status()
        self.assertFalse(status["auto_install"])
        self.assertFalse(status["auto_execute"])
        self.assertIn("mcp", [item["id"] for item in status["categories"]])

    @patch("brain_v12.brain.open_source_registry.httpx.get")
    def test_category_search_uses_category_and_preserves_safety_flags(self, get):
        response = Mock()
        response.json.return_value = {"items": [repo("owner/mcp-tool", "Apache-2.0")]}
        response.raise_for_status.return_value = None
        get.return_value = response

        result = self.registry.search("server", category="mcp", limit=5)

        self.assertTrue(result["ok"])
        self.assertEqual(result["category"], "mcp")
        self.assertTrue(result["tools"][0]["security_review_required"])
        self.assertFalse(result["tools"][0]["executable"])
        self.assertIn("model context protocol MCP server", get.call_args.kwargs["params"]["q"])

    def test_unknown_category_is_rejected(self):
        result = self.registry.search("anything", category="install-everything")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "INVALID_CATEGORY")
        self.assertEqual(result["tools"], [])


if __name__ == "__main__":
    unittest.main()
