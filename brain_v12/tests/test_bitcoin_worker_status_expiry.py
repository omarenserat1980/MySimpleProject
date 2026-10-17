"""Regression tests for mining worker live-status expiry."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from brain_v12.brain import bitcoin_worker_api as api


class WorkerStatusExpiryTests(unittest.TestCase):
    def setUp(self) -> None:
        api._latest.clear()
        self.auth = patch.dict(os.environ, {"BRAIN_MINING_WORKER_API_TOKEN": "x" * 40})
        self.auth.start()
        self.addCleanup(self.auth.stop)

    def tearDown(self) -> None:
        api._latest.clear()

    def test_status_removes_records_older_than_ttl(self) -> None:
        now = 10_000.0
        api._latest["stale-worker"] = {
            "worker_id": "stale-worker",
            "received_at": now - api.REPORT_TTL_SECONDS - 1,
            "online": True,
        }
        with patch.object(api.time, "time", return_value=now):
            result = api.worker_status("Bearer " + "x" * 40)
        self.assertEqual(result["worker_count"], 0)
        self.assertEqual(result["workers"], [])
        self.assertNotIn("stale-worker", api._latest)

    def test_status_keeps_fresh_records_online(self) -> None:
        now = 20_000.0
        api._latest["fresh-worker"] = {
            "worker_id": "fresh-worker",
            "received_at": now - api.REPORT_TTL_SECONDS,
            "online": False,
        }
        with patch.object(api.time, "time", return_value=now):
            result = api.worker_status("Bearer " + "x" * 40)
        self.assertEqual(result["worker_count"], 1)
        self.assertTrue(result["workers"][0]["online"])
        self.assertEqual(result["workers"][0]["worker_id"], "fresh-worker")


    def test_worker_heartbeat_rejects_unsafe_worker_id(self) -> None:
        with self.assertRaises(Exception):
            api.WorkerHeartbeat(
                worker_id="worker/with/slash",
                algorithm="sha256d",
                hashrate_hs=0,
                accepted_shares=0,
                rejected_shares=0,
                stale_shares=0,
                observed_at=1,
            )


if __name__ == "__main__":
    unittest.main()
