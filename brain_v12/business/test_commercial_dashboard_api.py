"""API tests for the read-only commercial dashboard."""
import unittest

from fastapi.testclient import TestClient

from brain_v12.app import app


class CommercialDashboardAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_endpoint(self):
        response = self.client.get("/api/commercial/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["capabilities"], 5)
        self.assertEqual(payload["verified_revenue"], 0.0)
        self.assertEqual(payload["verified_profit"], 0.0)
        self.assertTrue(payload["engineering_green_is_not_revenue"])

    def test_offers_endpoint_is_read_only(self):
        response = self.client.get("/api/commercial/offers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["offers"]), 5)


if __name__ == "__main__":
    unittest.main()
