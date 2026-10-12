import unittest

from brain_v12.tools.open_source_tool_hub import load_catalog, list_tools


class OpenSourceToolHubTests(unittest.TestCase):
    def test_catalog_loads_and_has_expected_domains(self):
        catalog = load_catalog()
        self.assertEqual(catalog["schema_version"], 1)
        self.assertEqual(
            {item["id"] for item in catalog["categories"]},
            {"boot_virtualization", "local_ai", "electronics"},
        )

    def test_ids_are_unique_and_tools_have_upstream_and_license(self):
        catalog = load_catalog()
        tools = list_tools(catalog)
        ids = [tool["id"] for tool in tools]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(tools), 10)
        for tool in tools:
            self.assertTrue(tool["repo"].startswith("https://"))
            self.assertTrue(tool["license"])

    def test_category_filter(self):
        catalog = load_catalog()
        tools = list_tools(catalog, "local_ai")
        self.assertTrue(tools)
        self.assertTrue(all(tool["category"] == "local_ai" for tool in tools))
        self.assertIn("ollama", {tool["id"] for tool in tools})

    def test_unknown_category_returns_empty(self):
        self.assertEqual(list_tools(load_catalog(), "unknown"), [])


if __name__ == "__main__":
    unittest.main()
