"""Tests for the commercial KPI evidence report."""
import unittest

from brain_v12.business.commercial_kpi_report import build_commercial_kpi_report
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG
from brain_v12.business.monetization_registry import MonetizationEntry


class CommercialKPIReportTests(unittest.TestCase):
    def test_initial_catalog_has_no_verified_revenue(self):
        report = build_commercial_kpi_report(INITIAL_MONETIZATION_CATALOG)
        self.assertEqual(report.capability_count, 5)
        self.assertEqual(report.verified_revenue, 0.0)
        self.assertEqual(report.verified_costs, 0.0)
        self.assertEqual(report.verified_profit, 0.0)
        self.assertTrue(report.evidence_gaps)

    def test_revenue_and_costs_are_summed_from_records(self):
        entries = [
            MonetizationEntry(
                capability_id="a",
                capability_name="A",
                offer="offer",
                target_customer="customer",
                acquisition_channel="direct",
                delivery_evidence="delivery",
                cost_model="tracked",
                status="REVENUE_REALIZED",
                realized_revenue=120.0,
                evidence_refs=["payment:a"],
            ),
            MonetizationEntry(
                capability_id="b",
                capability_name="B",
                offer="offer",
                target_customer="customer",
                acquisition_channel="direct",
                delivery_evidence="delivery",
                cost_model="tracked",
                status="PROFIT_VERIFIED",
                realized_revenue=80.0,
                verified_costs=30.0,
                evidence_refs=["payment:b", "cost:b"],
            ),
        ]
        report = build_commercial_kpi_report(entries)
        self.assertEqual(report.verified_revenue, 200.0)
        self.assertEqual(report.verified_costs, 30.0)
        self.assertEqual(report.verified_profit, 170.0)

    def test_report_explicitly_separates_engineering_from_revenue(self):
        record = build_commercial_kpi_report(INITIAL_MONETIZATION_CATALOG).to_record()
        self.assertTrue(record["engineering_green_is_not_revenue"])


if __name__ == "__main__":
    unittest.main()
