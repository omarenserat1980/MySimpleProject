from __future__ import annotations

import unittest

from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.golden_closed_loop import GoldenClosedLoop, GoldenTask


class GoldenClosedLoopTests(unittest.TestCase):
    def make_loop(self, *, fail_execute_once=False):
        store = EvidenceStore(":memory:")
        calls = {"execute": 0, "recover": 0}

        def authorize(task, attempt):
            return {"ok": True, "verified": True, "admit": True}

        def execute(task, attempt, key):
            calls["execute"] += 1
            if fail_execute_once and calls["execute"] == 1:
                return {"ok": False}
            return {"ok": True, "value": "real-result"}

        def observe(task, attempt, result):
            return {"ok": result.get("ok") is True, "observed": result}

        def verify(task, attempt, result, observation):
            return {"ok": result.get("ok") is True, "status": "VERIFIED"}

        def commit(task, attempt, verified):
            return {"ok": True, "committed": True}

        def learn(task, attempt, verified):
            return {"ok": True, "learned": True}

        def recover(task, attempt, error):
            calls["recover"] += 1
            return {"ok": True, "recovered": True}

        loop = GoldenClosedLoop(
            evidence_store=store,
            authorize=authorize,
            execute=execute,
            observe=observe,
            verify=verify,
            commit=commit,
            learn=learn,
            recover=recover,
            sleep_fn=lambda _: None,
        )
        return loop, calls, store

    def test_success_closes_only_after_verification_commit_and_learn(self):
        loop, calls, store = self.make_loop()
        result = loop.run(GoldenTask("t1", "demo"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "GOLDEN_CLOSED_LOOP_VERIFIED")
        self.assertEqual(
            result["transitions"],
            ["INTENT", "PLAN", "AUTHORITY", "EXECUTE", "OBSERVE", "VERIFY", "COMMIT", "LEARN", "CLOSED"],
        )
        self.assertGreaterEqual(len(store.for_task("t1")), 9)

    def test_failed_execution_recovers_and_retries(self):
        loop, calls, _ = self.make_loop(fail_execute_once=True)
        result = loop.run(GoldenTask("t2", "demo", max_attempts=2))
        self.assertTrue(result["ok"])
        self.assertEqual(calls["execute"], 2)
        self.assertEqual(calls["recover"], 1)
        self.assertIn("RECOVER", result["transitions"])

    def test_no_false_success_when_verification_fails(self):
        loop, _, _ = self.make_loop()

        loop.verify = lambda task, attempt, result, observation: {
            "ok": False, "status": "TAMPERED"
        }
        result = loop.run(GoldenTask("t3", "demo", max_attempts=1))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "GOLDEN_CLOSED_LOOP_FAILED")

    def test_authority_failure_cannot_execute(self):
        loop, calls, _ = self.make_loop()
        loop.authorize = lambda task, attempt: {"ok": False, "verified": False}
        result = loop.run(GoldenTask("t4", "demo", max_attempts=1))
        self.assertFalse(result["ok"])
        self.assertEqual(calls["execute"], 0)


if __name__ == "__main__":
    unittest.main()
