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


def attestation(**overrides):
    values = dict(
        verified=True,
        replay_protected=True,
        attestation_digest="digest-v1",
        challenge="challenge-123",
        executor_id="windows-native-vivobook-01",
        server_id="vivobook-01",
        brain_generation=8,
        network_generation=7,
    )
    values.update(overrides)
    return values


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
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            attestation=attestation(),
            brain_generation=8,
            fencing_token=19,
        )
        metadata = contract.execution_metadata()
        self.assertEqual(WINDOWS_NATIVE_EXECUTOR, metadata["executor"])
        self.assertEqual(7, metadata["network_generation"])
        self.assertEqual("digest-v1", metadata["attestation_digest"])

    def test_missing_agent_attestation_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            attestation={"verified": False},
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "attestation_not_verified"):
            contract.validate()

    def test_missing_replay_protection_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            attestation=attestation(replay_protected=False),
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "replay_protection"):
            contract.validate()

    def test_attestation_identity_mismatch_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            attestation=attestation(executor_id="other-executor"),
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "executor_mismatch"):
            contract.validate()

    def test_fencing_mismatch_fails_closed(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(),
            attestation=attestation(),
            brain_generation=8,
            fencing_token=18,
        )
        with self.assertRaisesRegex(ValueError, "fencing_mismatch"):
            contract.validate()

    def test_non_ready_server_cannot_execute(self):
        contract = WindowsNativeExecutorContract(
            executor_id="windows-native-vivobook-01",
            server=ready_server(state=NodeTrustState.ATTESTED),
            attestation=attestation(),
            brain_generation=8,
            fencing_token=19,
        )
        with self.assertRaisesRegex(ValueError, "not_ready"):
            contract.validate()


if __name__ == "__main__":
    unittest.main()
