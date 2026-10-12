import unittest

from brain_v12.brain.windows_server_network_contract import (
    ClientIdentity,
    NetworkTransition,
    NetworkZone,
    NodeTrustState,
    WINDOWS_SERVER_CLIENT_GATEWAY,
    WINDOWS_SERVER_NATIVE,
    WindowsServerNetworkContract,
    validate_network_boundary,
)


def ready_server(**overrides):
    values = dict(
        server_id="vivobook-01",
        brain_id="brain-01",
        network_generation=4,
        state=NodeTrustState.READY,
        capabilities=frozenset({WINDOWS_SERVER_NATIVE, WINDOWS_SERVER_CLIENT_GATEWAY}),
        client_ids=frozenset({"client-01"}),
        fencing_token=73,
        attestation_verified=True,
        firewall_policy_version="network-policy-v1",
    )
    values.update(overrides)
    return WindowsServerNetworkContract(**values)


class WindowsServerNetworkContractTests(unittest.TestCase):
    def test_ready_server_requires_attestation_firewall_and_fencing(self):
        ready_server().validate()

    def test_ready_server_without_attestation_fails_closed(self):
        with self.assertRaises(ValueError):
            ready_server(attestation_verified=False).validate()

    def test_ready_server_without_fencing_fails_closed(self):
        with self.assertRaises(ValueError):
            ready_server(fencing_token=None).validate()

    def test_management_and_internet_cannot_share_zone(self):
        with self.assertRaises(ValueError):
            ready_server(internet_zone=NetworkZone.MANAGEMENT).validate()

    def test_client_must_match_network_generation_and_registration(self):
        client = ClientIdentity(
            client_id="client-01",
            device_id="device-01",
            key_id="key-01",
            agent_version="1.0",
            capabilities=frozenset({"python.execute"}),
            network_generation=4,
        )
        self.assertTrue(ready_server().can_accept_client(client))

        wrong_generation = ClientIdentity(
            client_id="client-01",
            device_id="device-01",
            key_id="key-01",
            agent_version="1.0",
            network_generation=3,
        )
        self.assertFalse(ready_server().can_accept_client(wrong_generation))

    def test_quarantined_server_rejects_boundary(self):
        server = ready_server(state=NodeTrustState.QUARANTINED)
        with self.assertRaises(PermissionError):
            validate_network_boundary(server=server)

    def test_transition_is_monotonic_and_fail_closed(self):
        NetworkTransition(
            NodeTrustState.ENROLLED,
            NodeTrustState.ATTESTED,
            "attestation verified",
        ).validate()
        with self.assertRaises(ValueError):
            NetworkTransition(
                NodeTrustState.ENROLLED,
                NodeTrustState.READY,
                "skip trust stages",
            ).validate()


if __name__ == "__main__":
    unittest.main()
