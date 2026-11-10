"""Persistence tests for the commercial case SQLite store."""
import tempfile
import unittest
from pathlib import Path

from brain_v12.business.commercial_case import CommercialCase
from brain_v12.business.commercial_case_store import CommercialCaseStore


class CommercialCaseStoreTests(unittest.TestCase):
    def test_case_and_unverified_reference_survive_store_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.sqlite3"
            first = CommercialCaseStore(path)
            first.create_case(CommercialCase(
                case_id="persist-1",
                capability_id="digital-commerce",
                offer="Test offer",
            ))
            updated = first.add_evidence_reference(
                "persist-1", "payment", "receipt://test/42"
            )
            self.assertIsNotNone(updated)
            self.assertEqual(updated.stage(), "OFFER_DEFINED")

            reopened = CommercialCaseStore(path)
            case = reopened.get_case("persist-1")
            self.assertIsNotNone(case)
            self.assertEqual(case.stage(), "OFFER_DEFINED")
            self.assertEqual(len(case.evidence_refs), 1)
            self.assertEqual(case.evidence_refs[0]["verification_state"], "UNVERIFIED")

    def test_duplicate_case_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CommercialCaseStore(Path(directory) / "cases.sqlite3")
            case = CommercialCase(case_id="duplicate", capability_id="x", offer="y")
            store.create_case(case)
            with self.assertRaisesRegex(ValueError, "CASE_EXISTS"):
                store.create_case(case)

    def test_unknown_case_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(CommercialCaseStore(Path(directory) / "cases.sqlite3").get_case("missing"))


if __name__ == "__main__":
    unittest.main()
