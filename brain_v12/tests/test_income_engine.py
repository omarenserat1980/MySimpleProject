import unittest
from datetime import datetime, timezone

from brain.income_engine import IncomeEngine


class _Store:
    def __init__(self):
        self.rows = {}
        self.events = []

    def income_opportunities(self, limit=500):
        return list(self.rows.values())

    def upsert_income_opportunity(self, item):
        self.rows[item["opportunity_id"]] = {
            "opportunity_id": item["opportunity_id"],
            "data": dict(item),
        }

    def event(self, kind, payload):
        self.events.append((kind, payload))


class IncomeEngineTests(unittest.TestCase):
    def test_canonical_url_removes_tracking_and_trailing_slash(self):
        url = "https://Example.com/projects/123/?utm_source=x&fbclid=y&lang=ar"
        self.assertEqual(
            IncomeEngine._canonical_url(url),
            "https://example.com/projects/123?lang=ar",
        )

    def test_same_url_with_tracking_is_deduplicated(self):
        store = _Store()
        engine = IncomeEngine(store)
        retrieved = datetime.now(timezone.utc).isoformat()
        items = [
            {
                "title": "Build Python API",
                "url": "https://example.com/project/123/?utm_source=a",
                "source": "Example",
                "retrieved_at": retrieved,
                "requirements": "Python FastAPI REST API",
            },
            {
                "title": "Build Python API",
                "url": "https://example.com/project/123/?utm_source=b",
                "source": "Example",
                "retrieved_at": retrieved,
                "requirements": "Python FastAPI REST API",
            },
        ]
        accepted = engine.ingest_live_opportunities(items)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(store.rows), 1)

    def test_fit_score_uses_matching_skills(self):
        score, matches = IncomeEngine._fit_score(
            "Python FastAPI API automation",
            "Build REST API and automate workflow",
            "FREELANCE_JOB",
        )
        self.assertGreaterEqual(score, 50)
        self.assertIn("python", matches)
        self.assertIn("api", matches)
        self.assertIn("automation", matches)


if __name__ == "__main__":
    unittest.main()
