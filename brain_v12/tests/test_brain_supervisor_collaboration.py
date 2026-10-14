import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.brain.multi_agent_collaboration import AgentRole, TaskEnvelope


class BrainSupervisorCollaborationIntegrationTests(unittest.TestCase):
    def test_task_creation_and_snapshot_are_audited(self):
        with tempfile.TemporaryDirectory() as root:
            supervisor = BrainSupervisor(root=root)
            envelope = TaskEnvelope(
                task_id="integration-task",
                objective="Verify collaboration supervisor integration",
                role=AgentRole.IMPLEMENTER,
                repository="omarenserat1980/MySimpleProject",
                branch="feat/integration-task",
                base_commit="base123",
                allowed_paths=("brain_v12/brain/example.py",),
                acceptance_criteria=("audit-record-created",),
                idempotency_key="integration-idem",
            )
            task = supervisor.create_collaboration_task(envelope)
            self.assertEqual(task.envelope.task_id, "integration-task")
            record = supervisor.collaboration_record("integration-task")
            self.assertEqual(record["state"], "CREATED")
            rows = [json.loads(line) for line in Path(supervisor.events_path).read_text().splitlines()]
            events = [row["event"] for row in rows]
            self.assertIn("collaboration_task_created", events)
            self.assertIn("collaboration_snapshot", events)


if __name__ == "__main__":
    unittest.main()
