import unittest
from brain_v12.brain.multi_agent_collaboration import AgentRole, CollaborationCoordinator, CollaborationState, EvidenceRecord, TaskEnvelope

def make_envelope(task_id="task-1", paths=("brain_v12/brain/example.py",)):
    return TaskEnvelope(task_id, "Implement collaboration controls", AgentRole.IMPLEMENTER,
        "omarenserat1980/MySimpleProject", "feat/" + task_id, "base123",
        paths, ("unit-tests-pass", "independent-review-pass"), "idem-" + task_id, max_attempts=2)

def ready_to_verify(coordinator):
    coordinator.create_task(make_envelope())
    coordinator.mark_planned("task-1", planner_id="planner-A")
    coordinator.mark_ready("task-1")
    coordinator.start_implementation("task-1", implementer_id="coder-A", head_commit="base123")
    coordinator.submit_for_review("task-1", implementer_id="coder-A", head_commit="head456")
    coordinator.record_review("task-1", reviewer_id="reviewer-B", approved=True)

class MultiAgentCollaborationTests(unittest.TestCase):
    def test_role_and_path_permissions(self):
        self.assertTrue(CollaborationCoordinator.authorize_path(AgentRole.IMPLEMENTER, "brain_v12/brain/x.py", ("brain_v12/brain",)))
        self.assertFalse(CollaborationCoordinator.authorize_path(AgentRole.REVIEWER, "brain_v12/brain/x.py", ("brain_v12/brain",)))
        self.assertFalse(CollaborationCoordinator.authorize_path(AgentRole.IMPLEMENTER, "brain_v12/other.py", ("brain_v12/brain",)))

    def test_path_reservation_detects_overlap(self):
        c = CollaborationCoordinator()
        c.create_task(make_envelope("one", ("brain_v12/brain",)))
        c.create_task(make_envelope("two", ("brain_v12/tests",)))
        c.reserve_paths("one", ("brain_v12/brain",))
        with self.assertRaises(ValueError):
            c.reserve_paths("two", ("brain_v12/brain/x.py",))

    def test_reviewer_must_be_independent(self):
        c = CollaborationCoordinator()
        c.create_task(make_envelope())
        c.mark_planned("task-1", planner_id="planner-A")
        c.mark_ready("task-1")
        c.start_implementation("task-1", implementer_id="coder-A", head_commit="base123")
        c.submit_for_review("task-1", implementer_id="coder-A", head_commit="head456")
        with self.assertRaisesRegex(ValueError, "reviewer_must_be_independent"):
            c.record_review("task-1", reviewer_id="coder-A", approved=True)

    def test_wrong_commit_evidence_rejected(self):
        c = CollaborationCoordinator()
        ready_to_verify(c)
        evidence = EvidenceRecord.create(task_id="task-1", attempt_id="task-1:1",
            tested_commit="old", kind="unit-tests", payload={"exit_code": 0})
        with self.assertRaisesRegex(ValueError, "evidence_commit_mismatch"):
            c.add_evidence("task-1", evidence)

    def test_missing_evidence_blocks(self):
        c = CollaborationCoordinator()
        ready_to_verify(c)
        task = c.finalize("task-1", criteria_results={"unit-tests-pass": True, "independent-review-pass": True},
            required_evidence_kinds=("unit-tests",))
        self.assertEqual(task.state, CollaborationState.BLOCKED)

    def test_valid_evidence_and_criteria_accept(self):
        c = CollaborationCoordinator()
        ready_to_verify(c)
        evidence = EvidenceRecord.create(task_id="task-1", attempt_id="task-1:1",
            tested_commit="head456", kind="unit-tests", payload={"exit_code": 0, "passed": 8})
        c.add_evidence("task-1", evidence)
        task = c.finalize("task-1", criteria_results={"unit-tests-pass": True, "independent-review-pass": True},
            required_evidence_kinds=("unit-tests",))
        self.assertEqual(task.state, CollaborationState.ACCEPTED)
        self.assertEqual(c.export_record("task-1")["head_commit"], "head456")

if __name__ == "__main__":
    unittest.main()
