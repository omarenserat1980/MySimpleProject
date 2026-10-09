import os
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_authority import authority_proof
from brain_v12.brain.brain_identity import IDENTITY_SCHEMA
from brain_v12.brain.brain_leadership import BrainLeadershipStore
from brain_v12.brain.windows_execution_contract_issuer import issue_windows_contract


class WindowsExecutionContractIssuerTests(unittest.TestCase):
    def test_issuer_requires_authority_and_fencing(self):
        identity = {
            "schema": IDENTITY_SCHEMA,
            "brain_id": "brain-primary",
            "generation": 2,
            "source_commit": "a" * 40,
            "checkpoint_id": "BRAIN-GOLDEN-01",
        }
        checkpoint = {
            "checkpoint_id": "BRAIN-GOLDEN-01",
            "source_commit": "a" * 40,
            "status": "STABLE_BASELINE",
        }
        with tempfile.TemporaryDirectory() as d:
            store = BrainLeadershipStore(Path(d) / "leadership.db")
            lease = store.acquire(identity, checkpoint, "windows-real-boot-qemu", now=100)
            os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"] = "approval-secret"
            os.environ["BRAIN_AUTHORITY_SIGNING_TOKEN"] = "signing-secret"
            try:
                contract = issue_windows_contract(
                    identity=identity,
                    checkpoint=checkpoint,
                    lease=lease,
                    source_commit="a" * 40,
                    task_id="windows-real-boot",
                    attempt_id="attempt-1",
                    capability_verified=True,
                    human_approval_token="approval-secret",
                    now=100,
                )
            finally:
                os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN", None)
                os.environ.pop("BRAIN_AUTHORITY_SIGNING_TOKEN", None)
                store.close()

        self.assertEqual(contract["status"], "VERIFIED")
        self.assertEqual(contract["authority_decision"], "AUTHORIZED")
        self.assertEqual(contract["fencing_token"], 1)

        os.environ["BRAIN_AUTHORITY_SIGNING_TOKEN"] = "signing-secret"
        try:
            self.assertEqual(contract["authority_proof"], authority_proof(contract))
        finally:
            os.environ.pop("BRAIN_AUTHORITY_SIGNING_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
