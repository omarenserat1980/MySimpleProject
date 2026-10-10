import unittest

from brain_v12.brain.executor_contract import ExecutorRequest, ExecutorResult


class ExecutorContractTests(unittest.TestCase):
    def request(self, **overrides):
        values = dict(operation="python.test", task_id="task-1",
                      idempotency_key="idem-1", context={"suite": "smoke"},
                      permissions=frozenset(), constraints={"timeout_seconds": 30})
        values.update(overrides)
        return ExecutorRequest(**values)

    def test_request_hash_is_stable_and_round_trips(self):
        request = self.request()
        self.assertEqual(request.intent_hash, request.computed_intent_hash())
        self.assertEqual(request.to_dict()["schema_version"], "1.0")

    def test_rejects_secret_fields_in_context(self):
        with self.assertRaisesRegex(ValueError, "SECRET_MATERIAL"):
            self.request(context={"api_token": "do-not-store"})

    def test_rejects_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError, "INTENT_HASH_MISMATCH"):
            self.request(intent_hash="wrong")

    def test_rejects_unsupported_schema(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_SCHEMA_VERSION"):
            self.request(schema_version="9.0")

    def test_completed_is_not_verified_completed(self):
        result = ExecutorResult(status="COMPLETED", task_id="task-1",
                                idempotency_key="idem-1")
        self.assertEqual(result.status, "COMPLETED")

    def test_verified_completion_requires_evidence_and_objective_verification(self):
        with self.assertRaisesRegex(ValueError, "REQUIRES_OBJECTIVE"):
            ExecutorResult(status="VERIFIED_COMPLETED", task_id="task-1",
                           idempotency_key="idem-1",
                           verification_data={"objective_verified": True})

    def test_failed_requires_error(self):
        with self.assertRaisesRegex(ValueError, "REQUIRES_ERROR"):
            ExecutorResult(status="FAILED", task_id="task-1",
                           idempotency_key="idem-1")


if __name__ == "__main__":
    unittest.main()
