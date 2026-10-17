"""Regression coverage for the Bitcoin Mining Intelligence status route."""
import unittest

from brain_v12.brain.bitcoin_mining_intelligence_api import (
    bitcoin_mining_status,
    router,
)


class BitcoinMiningStatusRouteTests(unittest.TestCase):
    def test_status_route_is_bound_to_status_payload_not_budget_helper(self):
        status_routes = [
            route
            for route in router.routes
            if getattr(route, "path", None) == "/api/bitcoin-mining/status"
            and "GET" in (getattr(route, "methods", set()) or set())
        ]
        self.assertEqual(len(status_routes), 1)
        self.assertIs(status_routes[0].endpoint, bitcoin_mining_status)

        payload = status_routes[0].endpoint()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["execution_mode"], "ANALYSIS_AND_DRY_RUN_ONLY")
        self.assertFalse(payload["real_mining_enabled"])
        self.assertEqual(payload["verified_revenue_jod"], 0.0)


if __name__ == "__main__":
    unittest.main()
