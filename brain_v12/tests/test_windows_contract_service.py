"""Tests for Control Plane / executor capability separation."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from brain_v12.brain import windows_contract_service as service


class WindowsContractServiceTopologyTests(unittest.TestCase):
    def test_control_plane_without_local_qemu_can_issue_authorized_contract(self):
        """Control Plane host need not itself be the QEMU/KVM executor."""
        env = {
            "BRAIN_IDENTITY_FILE": "/control/identity.json",
            "BRAIN_CHECKPOINT_FILE": "/control/checkpoint.json",
            "BRAIN_LEADERSHIP_LEASE_FILE": "/control/lease.json",
            "BRAIN_OWNER_APPROVAL_FILE": "/control/owner-approval.json",
            "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64": "public-key",
            "BRAIN_WINDOWS_CONTRACT_OUTPUT": "/run/brain/contract.json",
            "BRAIN_HUMAN_APPROVAL_TOKEN": "approval-token",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(service, "capability_probe", return_value={
                 "verified": False,
                 "scope": "control-plane-host-diagnostic-only",
                 "checks": {"qemu": False, "kvm": False},
             }), \
             patch.object(service, "issue_from_files", return_value={
                 "verified": True,
                 "contract_path": "/run/brain/contract.json",
                 "schema": "brain.windows-execution-contract.v1",
             }) as issuer:
            result = service.issue({
                "source_commit": "a" * 40,
                "task_id": "windows-server-2025-real-boot",
                "attempt_id": "github-123-attempt-1",
            })

        self.assertTrue(result["verified"])
        self.assertFalse(result["capability"]["verified"])
        self.assertEqual(result["capability"]["scope"], "control-plane-host-diagnostic-only")
        self.assertTrue(issuer.call_args.kwargs["capability_verified"])
        self.assertEqual(issuer.call_args.kwargs["source_commit"], "a" * 40)

    def test_missing_request_binding_is_rejected_before_issuance(self):
        with patch.object(service, "issue_from_files") as issuer:
            with self.assertRaisesRegex(RuntimeError, "WINDOWS_CONTRACT_REQUEST_ATTEMPT_ID_REQUIRED"):
                service.issue({"source_commit": "a" * 40, "task_id": "task", "attempt_id": ""})
            issuer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
