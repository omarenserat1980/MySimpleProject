import os
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_db = ROOT / ".brain" / "test" / "brain-v12-test.db"
        test_db.parent.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("BRAIN_DB", str(test_db))
        os.environ.setdefault("BRAIN_LIVE_INCOME_SEARCH_ENABLED", "false")
        os.environ.setdefault("BRAIN_WORKFORCE_ENABLED", "false")

    def test_preflight_module_imports(self):
        from brain_v12.tools import ci_preflight
        self.assertTrue(callable(ci_preflight.main))

    def test_dockerfile_has_runtime_healthcheck(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/health", dockerfile)

    def test_required_runtime_routes(self):
        from brain_v12.app import app

        routes = {getattr(route, "path", "") for route in app.routes}
        self.assertTrue({"/health", "/api/system/readiness", "/api/deploy/verify"} <= routes)

    def test_health_contract_without_external_services(self):
        from fastapi.testclient import TestClient
        from brain_v12.app import app

        with patch.dict(
            os.environ,
            {
                "BRAIN_LIVE_INCOME_SEARCH_ENABLED": "false",
                "BRAIN_WORKFORCE_ENABLED": "false",
                "BRAIN_V14_VERSION": "14.0",
            },
            clear=False,
        ):
            response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "14.0")


if __name__ == "__main__":
    unittest.main()
