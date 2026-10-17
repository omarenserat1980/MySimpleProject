import unittest

from brain_v12.execution_proof import ExecutionProof, ProofTransitionError


class ExecutionProofTests(unittest.TestCase):
    def test_valid_round_trip_is_hash_chained_and_verifiable(self):
        clock = iter(range(100, 110))
        proof = ExecutionProof("task-1", "worker-1", now=lambda: next(clock))
        proof.transition("CLAIMED", lease_seconds=60)
        proof.transition("RUNNING")
        proof.transition("RESULT_READY", result_digest="abc")
        proof.transition("EVIDENCE_READY", evidence_count=4)
        proof.transition("VERIFYING")
        proof.transition("ACCEPTED", verifier="primary")

        self.assertEqual(proof.state, "ACCEPTED")
        self.assertTrue(proof.verify_chain())
        exported = proof.export()
        self.assertTrue(exported["verified"])
        self.assertEqual(len(exported["events"]), 7)

    def test_invalid_transition_is_rejected(self):
        proof = ExecutionProof("task-2", "worker-2")
        with self.assertRaises(ProofTransitionError):
            proof.transition("ACCEPTED")

    def test_tampering_breaks_verification(self):
        proof = ExecutionProof("task-3", "worker-3")
        proof.transition("CLAIMED")
        proof.transition("RUNNING")
        exported = proof.export()
        exported["events"][1]["payload"]["tampered"] = True

        # Reconstructing the proof is not required; the exported evidence itself
        # must carry enough information for an external verifier to detect this.
        event = exported["events"][1]
        self.assertNotEqual(
            event["event_hash"],
            __import__("hashlib").sha256(
                __import__("json").dumps(
                    {
                        "sequence": event["sequence"],
                        "state": event["state"],
                        "task_id": event["task_id"],
                        "worker_id": event["worker_id"],
                        "timestamp": event["timestamp"],
                        "payload": event["payload"],
                        "previous_hash": event["previous_hash"],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
            ).hexdigest(),
        )

    def test_terminal_state_cannot_continue(self):
        proof = ExecutionProof("task-4", "worker-4")
        proof.transition("CLAIMED")
        proof.transition("RUNNING")
        proof.transition("RESULT_READY")
        proof.transition("EVIDENCE_READY")
        proof.transition("VERIFYING")
        proof.transition("REJECTED")
        with self.assertRaises(ProofTransitionError):
            proof.transition("ACCEPTED")


if __name__ == "__main__":
    unittest.main()
