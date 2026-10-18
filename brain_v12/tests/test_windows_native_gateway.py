import unittest

from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.execution_policy import WINDOWS_NATIVE_EXECUTOR
from brain_v12.brain.windows_server_network_contract import (
    WINDOWS_SERVER_NATIVE,
    WINDOWS_SERVER_CLIENT_GATEWAY,
    NetworkZone,
)


def metadata(attested=True, fencing=19, state="READY"):
    return {
        "native_contract": {
            "executor_id": "windows-native-vivobook-01",
            "agent_attestation_verified": attested,
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
    def test_gateway_blocks_verified_native_contract_in_simulation_only_mode(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata()
            )

    def test_gateway_blocks_missing_agent_attestation_in_simulation_only_mode(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(attested=False)
            )

    def test_gateway_blocks_fencing_mismatch_in_simulation_only_mode(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(fencing=18)
            )

    def test_gateway_blocks_non_ready_server_in_simulation_only_mode(self):
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            BrainExecutionGateway().authorize_task(
                WINDOWS_NATIVE_EXECUTOR, metadata(state="ATTESTED")
            )


if __name__ == "__main__":
    unittest.main()
