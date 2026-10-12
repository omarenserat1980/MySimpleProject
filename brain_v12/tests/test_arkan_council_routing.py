import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_council import BrainCouncil


class BrainCouncilArkanIdentityTests(unittest.TestCase):
    def test_physical_arkan_heartbeat_is_diagnostic_not_executor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "council.sqlite"
            council = BrainCouncil(
                str(db),
                chatgpt_provider=object(),
                decision_engine=object(),
                device_reader=lambda: {
                    "ttl_seconds": 15,
                    "agents": [
                        {"agent_id": "arkan", "online": True, "state": "ONLINE"},
                    ],
                },
            )
            with council._connect() as con:
                con.execute(
                    "INSERT INTO brain_council_meetings(title,status,participants,agenda,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    ("test", "OPEN", "[]", "[]", "now", "now"),
                )
                con.commit()

            result = council.verify_device_presence(1)
            self.assertEqual(result["status"], "DEVICE_OBSERVED_NOT_EXECUTOR")
            self.assertEqual(result["executor_identity"], "brain-software-pipeline")
            self.assertFalse(result["presence"]["preferred_arkan"])
            self.assertFalse(result["presence"]["execution_eligible"])
            with council._connect() as con:
                participants = json.loads(con.execute(
                    "SELECT participants FROM brain_council_meetings WHERE id=1"
                ).fetchone()["participants"])
            self.assertEqual(participants[0]["role"], "device_observer_only")
            self.assertNotEqual(participants[0]["role"], "device_observer_and_execution_endpoint")


if __name__ == "__main__":
    unittest.main()
