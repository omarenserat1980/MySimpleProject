import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.robotics_research_memory import (
    MEMORY_KEY,
    PROJECTS,
    persist_to_memory,
    snapshot,
)


class RoboticsResearchMemoryTests(unittest.TestCase):
    def test_catalog_has_primary_links_and_explicit_license_review(self):
        data = snapshot()
        self.assertGreaterEqual(len(data["projects"]), 5)
        self.assertTrue(all(item["url"].startswith("https://") for item in data["projects"]))
        self.assertTrue(all(item.get("license_status") for item in data["projects"]))
        self.assertFalse(data["evidence_policy"]["live_hardware_or_agent_presence_proven"])
        self.assertFalse(data["evidence_policy"]["auto_install_dependencies"])
        self.assertFalse(data["evidence_policy"]["enable_external_actions"])

    def test_explicit_persist_round_trips_through_memory_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            result = persist_to_memory(store)
            saved = next(item for item in store.memories() if item["key"] == MEMORY_KEY)
            decoded = json.loads(saved["value"])
            self.assertTrue(result["ok"])
            self.assertEqual(result["project_count"], len(PROJECTS))
            self.assertEqual(len(decoded["projects"]), len(PROJECTS))
            self.assertEqual(decoded["evidence_policy"]["default_mode"],
                             "READ_ONLY_RESEARCH_AND_SOFTWARE_SIMULATION")
            self.assertTrue(any(event["kind"] == "OPEN_SOURCE_ROBOTICS_RESEARCH_CATALOG_SAVED"
                                for event in _events(store)))


def _events(store):
    with store.connect() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT kind, payload, created_at FROM events ORDER BY id"
        ).fetchall()]


if __name__ == "__main__":
    unittest.main()
