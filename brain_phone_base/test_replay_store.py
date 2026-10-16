import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path

from brain_phone_base.replay_store import ReplayStoreError, SQLiteReplayStore


class SQLiteReplayStoreTests(unittest.TestCase):
    def test_consumed_challenge_survives_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "replay.sqlite3"
            first = SQLiteReplayStore(database)
            first.consume("challenge-1", "2026-10-16T12:05:00Z", "2026-10-16T12:00:00Z")
            reopened = SQLiteReplayStore(database)
            self.assertTrue(reopened.contains("challenge-1"))
            with self.assertRaisesRegex(ReplayStoreError, "CHALLENGE_REPLAYED"):
                reopened.consume("challenge-1", "2026-10-16T12:05:00Z", "2026-10-16T12:00:01Z")


    def test_concurrent_consumption_has_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "replay.sqlite3"

            def consume():
                try:
                    SQLiteReplayStore(database).consume(
                        "challenge-race", "2026-10-16T12:05:00Z", "2026-10-16T12:00:00Z"
                    )
                    return "accepted"
                except ReplayStoreError as exc:
                    return exc.code

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: consume(), range(2)))
            self.assertEqual(results.count("accepted"), 1)
            self.assertEqual(results.count("CHALLENGE_REPLAYED"), 1)

    def test_invalid_id_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteReplayStore(Path(temp) / "replay.sqlite3")
            with self.assertRaisesRegex(ReplayStoreError, "CHALLENGE_ID_INVALID"):
                store.consume("  ", "2026-10-16T12:05:00Z", "2026-10-16T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
