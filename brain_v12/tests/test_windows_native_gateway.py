import unittest

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.execution_policy import WINDOWS_NATIVE_EXECUTOR
from brain_v12.brain.windows_server_network_contract import (
    WINDOWS_SERVER_NATIVE,
    WINDOWS_SERVER_CLIENT_GATEWAY,
    NetworkZone,
    NodeTrustState,
)


def metadata(attested=True, fencing=19, state="READY"):
    return {
        "native_contract": {
            "executor_id": "windows-native-vivobook-01",
            "attestation": {\n                "verified": attested,\n                "replay_protected": True,\n                "attestation_digest": "digest-v1",\n                "challenge": "challenge-123",\n                "executor_id": "windows-native-vivobook-01",\n                "server_id": "vivobook-01",\n                "brain_generation": 8,\n                "network_generation": 7,\n            },
            "brain_generation": 8,
            "fencing_token": fencing,
            "authority_policy_version": "authority-policy-v1",
            "state": "VERIFIED",
            "server": {
                "server_id": "vivobook-01",
                "brain_id": "brain-primary",
                "network_generation": 7,
                "management_zone": NetworkZone.MANAGEMENT.value,
                "client_zone": NetworkZone.CLIENT.value,
                "service_zone": NetworkZone.SERVICE.value,
                "internet_zone": NetworkZone.INTERNET.value,
                "state": state,
                "capabilities": [
                    WINDOWS_SERVER_NATIVE,
                    WINDOWS_SERVER_CLIENT_GATEWAY,
                ],
                "client_ids": ["redmi3-01"],
                "fencing_token": 19,
                "attestation_verified": True,
                "firewall_policy_version": "fw-v1",
            },
        }
    }


class WindowsNativeGatewayTests(unittest.TestCase):
    def test_gateway_requires_verified_native_contract(self):
        decision = BrainExecutionGateway().authorize_task(
            WINDOWS_NATIVE_EXECUTOR, metadata()
        )
        self.assertTrue(decision.verified)
        self.assertEqual(WINDOWS_NATIVE_EXECUTOR, decision.executor)

    def test_gateway_rejects_missing_agent_attestation(self):
        with self.assertRaisesRegex(ValueError, "attestation_not_verified"):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(attested=False)
            )

    def test_gateway_rejects_fencing_mismatch(self):
        with self.assertRaisesRegex(ValueError, "fencing_mismatch"):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(fencing=18)
            )

    def test_gateway_rejects_non_ready_server(self):
        with self.assertRaisesRegex(ValueError, "not_ready"):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(state="ATTESTED")
            )


if __name__ == "__main__":
    unittest.main()
