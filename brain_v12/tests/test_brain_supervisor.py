import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.brain.golden_acceptance_gate import AcceptanceCriterion


class SupervisorTests(unittest.TestCase):
    def test_repair_and_retry_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d, max_cycles=3)
            try:
                job = s.run_simulation("film", verification_ok=False)
                self.assertEqual(job["status"], "completed")
                events = Path(d, "events.jsonl").read_text(encoding="utf-8")
                self.assertIn('"repair"', events)
                self.assertIn('"retry"', events)
            finally:
                s.evidence.close()

    def test_next_action_uses_verification_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d, max_cycles=2)
            try:
                job = s.create("film")
                self.assertEqual(s.next_action(job, {"ok": True})["action"], "deliver")
                self.assertEqual(s.next_action(job, {"ok": False})["action"], "retry_backend")
            finally:
                s.evidence.close()

    def test_external_actions_require_gate(self):
        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d)
            try:
                self.assertFalse(s.authorize_external("move_money")["allowed"])
                self.assertTrue(s.authorize_external("move_money", approved=True)["allowed"])
            finally:
                s.evidence.close()

    def _prepare_verifying_job(self, supervisor):
        job = supervisor.create("golden acceptance integration")
        for phase in ("discover", "plan", "select_backend", "execute", "observe", "verify"):
            job = supervisor.transition(
                job, phase, details={"test_fixture": True}, enforce_authority=False
            )
        return job

    def _append_golden_evidence(self, supervisor, job, *, include_independent=True):
        task_id = job["job_id"]
        mission = supervisor.missions[task_id]
        first = supervisor.evidence.append(
            task_id, "artifact_verified",
            {"artifact": "fixture.bin", "reality_level": "SIMULATED"},
            producer="fixture-executor", mission_id=task_id,
            attempt=mission.attempts, phase="VERIFYING",
        )
        second = supervisor.evidence.append(
            task_id, "runtime_check_passed",
            {"checks_passed": 1, "reality_level": "SIMULATED"},
            producer="fixture-executor", mission_id=task_id,
            attempt=mission.attempts, phase="VERIFYING",
        )
        if include_independent:
            supervisor.evidence.append(
                task_id, "independent_verification",
                {
                    "verified": True,
                    "reality_level": "SIMULATED",
                    "verified_evidence_ids": [first["evidence_id"], second["evidence_id"]],
                    "criterion_ids": ["artifact-exists", "runtime-check"],
                },
                producer="fixture-independent-verifier", mission_id=task_id,
                attempt=mission.attempts, phase="VERIFYING",
            )

    def test_golden_gate_is_wired_into_supervisor_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d)
            try:
                job = self._prepare_verifying_job(s)
                self._append_golden_evidence(s, job)
                result = s.deliver_if_golden(job, (
                    AcceptanceCriterion("artifact-exists", "artifact_verified"),
                    AcceptanceCriterion("runtime-check", "runtime_check_passed"),
                ))
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["phase"], "deliver")
                self.assertEqual(
                    result["details"]["golden_acceptance"]["status"],
                    "GOLDEN_LOOP_VERIFIED",
                )
                events = Path(d, "events.jsonl").read_text(encoding="utf-8")
                self.assertIn('"golden_acceptance_gate"', events)
            finally:
                s.evidence.close()

    def test_supervisor_delivery_is_blocked_without_independent_verification(self):
        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d)
            try:
                job = self._prepare_verifying_job(s)
                self._append_golden_evidence(s, job, include_independent=False)
                result = s.deliver_if_golden(job, (
                    AcceptanceCriterion("artifact-exists", "artifact_verified"),
                    AcceptanceCriterion("runtime-check", "runtime_check_passed"),
                ))
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["phase"], "blocked")
                self.assertEqual(
                    result["details"]["golden_acceptance"]["status"],
                    "INDEPENDENT_VERIFICATION_MISSING",
                )
            finally:
                s.evidence.close()


if __name__ == "__main__":
    unittest.main()
