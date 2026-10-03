"""Tests for the commercial operations dashboard."""
import unittest

from brain_v12.business.commercial_case import CommercialCase
from brain_v12.business.commercial_operations_dashboard import (
    build_commercial_operations_dashboard,
)
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG


class CommercialOperationsDashboardTests(unittest.TestCase):
    def test_initial_dashboard_is_zero_revenue(self):
        dashboard = build_commercial_operations_dashboard(
            INITIAL_MONETIZATION_CATALOG, []
        )
        self.assertEqual(dashboard.capabilities, 5)
        self.assertEqual(dashboard.cases, 0)
        self.assertEqual(dashboard.revenue, 0.0)
        self.assertEqual(dashboard.costs, 0.0)
        self.assertEqual(dashboard.profit, 0.0)

    def test_dashboard_exposes_next_action(self):
        case = CommercialCase(
            "case-1",
            "cinematic-factory",
            "short-film package",
            prospect_evidence="prospect:1",
        )
        dashboard = build_commercial_operations_dashboard(
            INITIAL_MONETIZATION_CATALOG, [case]
        )
        self.assertEqual(dashboard.cases, 1)
        self.assertEqual(
            dashboard.cases_needing_action[0]["next_evidence_required"],
            "customer_evidence",
        )

    def test_dashboard_never_turns_cases_into_revenue(self):
        case = CommercialCase(
            "case-2",
            "brain-automation-services",
            "automation package",
            customer_evidence="customer:2",
        )
        dashboard = build_commercial_operations_dashboard(
            INITIAL_MONETIZATION_CATALOG, [case]
        )
        self.assertEqual(dashboard.revenue, 0.0)
        self.assertEqual(dashboard.profit, 0.0)


if __name__ == "__main__":
    unittest.main()
