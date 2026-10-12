import unittest

from fastapi import HTTPException

from brain_v12.brain.open_source_tools_api import open_source_tool_detail, open_source_tools


class OpenSourceToolsApiTests(unittest.TestCase):
    def test_list_is_catalog_only_and_contains_expected_categories(self):
        # Call the HTTP route through FastAPI's TestClient so Query defaults
        # are resolved as they are in production requests.
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from brain_v12.brain.open_source_tools_api import router

        app = FastAPI()
        app.include_router(router)
        response = TestClient(app).get("/api/open-source-tools")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["mode"], "catalog_only")
        self.assertGreaterEqual(result["count"], 10)
        self.assertEqual(
            {item["id"] for item in result["categories"]},
            {"boot_virtualization", "local_ai", "electronics"},
        )

    def test_availability_preflight_is_non_executing(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from brain_v12.brain.open_source_tools_api import router

        app = FastAPI()
        app.include_router(router)
        response = TestClient(app).get("/api/open-source-tools/preflight/availability")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["mode"], "path_preflight_only")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["installation_enabled"])
        self.assertFalse(result["hardware_io_enabled"])
        self.assertEqual(result["summary"]["checked"], 9)
        self.assertEqual(len(result["tools"]), 9)

    def test_category_filter(self):
        result = open_source_tools("local_ai")
        self.assertTrue(result["tools"])
        self.assertTrue(all(item["category"] == "local_ai" for item in result["tools"]))
        self.assertIn("ollama", {item["id"] for item in result["tools"]})

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            open_source_tools("not-a-category")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_tool_detail(self):
        result = open_source_tool_detail("qemu")
        self.assertEqual(result["tool"]["name"], "QEMU")
        self.assertFalse(result["execution_enabled"])

    def test_missing_tool_is_404(self):
        with self.assertRaises(HTTPException) as ctx:
            open_source_tool_detail("not-a-tool")
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
