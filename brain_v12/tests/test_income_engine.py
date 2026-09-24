import unittest
from datetime import datetime, timezone

from brain_v12.brain.income_engine import IncomeEngine


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


    def test_unchanged_content_is_detected(self):
        store = _Store()
        engine = IncomeEngine(store)
        retrieved = datetime.now(timezone.utc).isoformat()
        item = {
            "title": "Build Arabic website",
            "url": "https://example.com/project/unchanged",
            "source": "Example",
            "retrieved_at": retrieved,
            "requirements": "Arabic website HTML CSS",
            "budget": "50 JOD",
            "posted_at": "2026-09-25",
        }
        first = engine.ingest_live_opportunities([item])
        self.assertEqual(first[0]["lifecycle"], "NEW")
        second_item = dict(item)
        second_item["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        second = engine.ingest_live_opportunities([second_item])
        self.assertEqual(second[0]["lifecycle"], "UNCHANGED")

    def test_changed_content_is_updated(self):
        store = _Store()
        engine = IncomeEngine(store)
        base = datetime.now(timezone.utc).isoformat()
        item = {
            "title": "Python API task",
            "url": "https://example.com/project/change",
            "source": "Example",
            "retrieved_at": base,
            "requirements": "Python API",
        }
        engine.ingest_live_opportunities([item])
        changed = dict(item)
        changed["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        changed["requirements"] = "Python API and automation"
        result = engine.ingest_live_opportunities([changed])
        self.assertEqual(result[0]["lifecycle"], "UPDATED")

    def test_stale_refresh_marks_old_live_opportunity(self):
        store = _Store()
        engine = IncomeEngine(store)
        item = {
            "title": "Old website task",
            "url": "https://example.com/project/stale",
            "source": "Example",
            "retrieved_at": "2020-01-01T00:00:00+00:00",
            "requirements": "Website",
        }
        engine.ingest_live_opportunities([item], max_age_hours=999999)
        result = engine.refresh_lifecycle(max_age_hours=1)
        self.assertEqual(result["stale"], 1)
        row = next(iter(store.rows.values()))
        self.assertEqual(row["data"]["lifecycle"], "STALE")

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
