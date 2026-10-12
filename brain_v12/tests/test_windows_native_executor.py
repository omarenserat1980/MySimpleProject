import unittest

from brain_v12.brain.windows_native_executor import (
    WINDOWS_NATIVE_EXECUTOR,
    WindowsNativeExecutorContract,
)
from brain_v12.brain.windows_server_network_contract import (
    WINDOWS_SERVER_NATIVE,
    WINDOWS_SERVER_CLIENT_GATEWAY,
    NetworkZone,
    NodeTrustState,
    WindowsServerNetworkContract,
)


def ready_server(**overrides):
    values = dict(
        server_id="vivobook-01",
        brain_id="brain-primary",
        network_generation=7,
        management_zone=NetworkZone.MANAGEMENT,
        client_zone=NetworkZone.CLIENT,
        service_zone=NetworkZone.SERVICE,
        internet_zone=NetworkZone.INTERNET,
        state=NodeTrustState.READY,
        capabilities=frozenset({WINDOWS_SERVER_NATIVE, WINDOWS_SERVER_CLIENT_GATEWAY}),
        client_ids=frozenset({"redmi3-01"}),
        fencing_token=19,
        attestation_verified=True,
        firewall_policy_version="fw-v1",
    )
    values.update(overrides)
    return WindowsServerNetworkContract(**values)


class WindowsNativeExecutorContractTests(unittest.TestCase):
    def test_ready_attested_vivobook_contract_is_verified(self):
        server = ready_server()
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=server,
            agent_attestation_verified=True,
            brain_generation=8,
            fencing_token=19,
        )
        metadata = contract.execution_metadata()
        self.assertEqual(WINDOWS_NATIVE_EXECUTOR, metadata["executor"])
        self.assertEqual(7, metadata["network_generation"])

    def test_missing_agent_attestation_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            agent_attestation_verified=False,
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "agent_attestation"):
            contract.validate()

    def test_fencing_mismatch_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            agent_attestation_verified=True,
            brain_generation=8,
            fencing_token=18,
        )
        with self.assertRaisesRegex(ValueError, "fencing_mismatch"):
            contract.validate()

    def test_non_ready_server_cannot_execute(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(state=NodeTrustState.ATTESTED),
            agent_attestation_verified=True,
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "not_ready"):
            contract.validate()


if __name__ == "__main__":
    unittest.main()
