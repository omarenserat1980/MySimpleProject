"""Windows Server Network trust contract.

This module models a native Windows Server as a Brain network node.
It deliberately does not provision firewall rules or open ports.  It
defines the security state that must be satisfied before a server or
client may participate in consequential Brain execution.

Trust is explicit:
  identity -> attestation -> network policy -> lease/fencing -> authority
  -> execution contract -> evidence -> independent verification.

A network connection alone never grants Brain authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet


WINDOWS_SERVER_NATIVE = "windows-server-native"
WINDOWS_SERVER_CLIENT_GATEWAY = "windows-server-client-gateway"


class NetworkZone(str, Enum):
    MANAGEMENT = "management"
    CLIENT = "client"
    SERVICE = "service"
    INTERNET = "internet"
    QUARANTINE = "quarantine"


class NodeTrustState(str, Enum):
    ENROLLED = "ENROLLED"
    ATTESTED = "ATTESTED"
    AUTHORIZED = "AUTHORIZED"
    READY = "READY"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class ClientIdentity:
    client_id: str
    device_id: str
    key_id: str
    agent_version: str
    capabilities: FrozenSet[str] = frozenset()
    network_generation: int = 1

    def validate(self) -> None:
        for name, value in (
            ("client_id", self.client_id),
            ("device_id", self.device_id),
            ("key_id", self.key_id),
            ("agent_version", self.agent_version),
        ):
            if not str(value).strip():
                raise ValueError(f"client_identity_{name}_required")
        if self.network_generation < 1:
            raise ValueError("client_identity_network_generation_invalid")


@dataclass(frozen=True)
class WindowsServerNetworkContract:
    server_id: str
    brain_id: str
    network_generation: int
    management_zone: NetworkZone = NetworkZone.MANAGEMENT
    client_zone: NetworkZone = NetworkZone.CLIENT
    service_zone: NetworkZone = NetworkZone.SERVICE
    internet_zone: NetworkZone = NetworkZone.INTERNET
    state: NodeTrustState = NodeTrustState.ENROLLED
    capabilities: FrozenSet[str] = frozenset()
    client_ids: FrozenSet[str] = frozenset()
    fencing_token: int | None = None
    attestation_verified: bool = False
    firewall_policy_version: str = ""
    metadata: dict = field(default_factory=dict)

    def validate(self) -> None:
        if not self.server_id.strip() or not self.brain_id.strip():
            raise ValueError("windows_server_identity_required")
        if self.network_generation < 1:
            raise ValueError("windows_server_network_generation_invalid")
        if self.management_zone == self.client_zone:
            raise ValueError("management_and_client_zones_must_be_separate")
        if self.management_zone == self.internet_zone:
            raise ValueError("management_and_internet_zones_must_be_separate")
        if self.state in {NodeTrustState.ATTESTED, NodeTrustState.AUTHORIZED, NodeTrustState.READY}:
            if not self.attestation_verified:
                raise ValueError("attestation_required_for_trusted_server_state")
            if not self.firewall_policy_version.strip():
                raise ValueError("firewall_policy_required_for_trusted_server_state")
        if self.state in {NodeTrustState.AUTHORIZED, NodeTrustState.READY}:
            if self.fencing_token is None or self.fencing_token < 1:
                raise ValueError("fencing_token_required_for_authorized_server")
        if WINDOWS_SERVER_NATIVE in self.capabilities and self.state == NodeTrustState.READY:
            if WINDOWS_SERVER_CLIENT_GATEWAY not in self.capabilities:
                raise ValueError("client_gateway_capability_required_for_network_node")

    def can_accept_client(self, client: ClientIdentity) -> bool:
        self.validate()
        client.validate()
        if self.state != NodeTrustState.READY:
            return False
        if client.network_generation != self.network_generation:
            return False
        if client.client_id in self.client_ids:
            return True
        return False

    def is_isolated(self) -> bool:
        return self.state in {NodeTrustState.QUARANTINED, NodeTrustState.REVOKED}


@dataclass(frozen=True)
class NetworkTransition:
    from_state: NodeTrustState
    to_state: NodeTrustState
    reason: str

    def validate(self) -> None:
        if not self.reason.strip():
            raise ValueError("network_transition_reason_required")
        allowed = {
            NodeTrustState.ENROLLED: {NodeTrustState.ATTESTED, NodeTrustState.QUARANTINED, NodeTrustState.REVOKED},
            NodeTrustState.ATTESTED: {NodeTrustState.AUTHORIZED, NodeTrustState.QUARANTINED, NodeTrustState.REVOKED},
            NodeTrustState.AUTHORIZED: {NodeTrustState.READY, NodeTrustState.QUARANTINED, NodeTrustState.REVOKED},
            NodeTrustState.READY: {NodeTrustState.QUARANTINED, NodeTrustState.REVOKED},
            NodeTrustState.QUARANTINED: {NodeTrustState.ATTESTED, NodeTrustState.REVOKED},
            NodeTrustState.REVOKED: set(),
        }
        if self.to_state not in allowed[self.from_state]:
            raise ValueError(
                f"invalid_network_transition:{self.from_state.value}->{self.to_state.value}"
            )


def validate_network_boundary(
    *,
    server: WindowsServerNetworkContract,
    client: ClientIdentity | None = None,
) -> None:
    """Fail closed before a client/network operation is authorized."""
    server.validate()
    if server.is_isolated():
        raise PermissionError("WINDOWS_SERVER_NETWORK_ISOLATED")
    if client is not None and not server.can_accept_client(client):
        raise PermissionError("CLIENT_NOT_AUTHORIZED_FOR_NETWORK_GENERATION")
