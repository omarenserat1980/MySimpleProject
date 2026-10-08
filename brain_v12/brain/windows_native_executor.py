"""Fail-closed contract for a physical/native Windows Server executor.

This is intentionally separate from the QEMU real-boot executor. It does not
execute commands or provision Windows; it validates the trust prerequisites
that must exist before a VivoBook-class Windows host can receive Brain work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .windows_server_network_contract import (
    WINDOWS_SERVER_NATIVE,
    WINDOWS_SERVER_CLIENT_GATEWAY,
    NodeTrustState,
    WindowsServerNetworkContract,
    validate_network_boundary,
)

WINDOWS_NATIVE_EXECUTOR = "windows-native-agent"


@dataclass(frozen=True)
class WindowsNativeExecutorContract:
    executor_id: str
    server: WindowsServerNetworkContract
    agent_attestation_verified: bool
    brain_generation: int
    fencing_token: int
    authority_policy_version: str = "authority-policy-v1"
    state: str = "VERIFIED"

    def validate(self) -> None:
        if not self.executor_id.strip():
            raise ValueError("windows_native_executor_id_required")
        if self.server.state != NodeTrustState.READY:
            raise ValueError("windows_native_server_not_ready")
        if WINDOWS_SERVER_NATIVE not in self.server.capabilities:
            raise ValueError("windows_native_capability_required")
        if WINDOWS_SERVER_CLIENT_GATEWAY not in self.server.capabilities:
            raise ValueError("windows_native_client_gateway_capability_required")
        if not self.agent_attestation_verified:
            raise ValueError("windows_native_agent_attestation_required")
        if self.brain_generation < 1:
            raise ValueError("windows_native_generation_invalid")
        if self.fencing_token < 1:
            raise ValueError("windows_native_fencing_required")
        if self.fencing_token != self.server.fencing_token:
            raise ValueError("windows_native_fencing_mismatch")
        if self.authority_policy_version != "authority-policy-v1":
            raise ValueError("windows_native_authority_policy_invalid")
        if self.state != "VERIFIED":
            raise ValueError("windows_native_contract_not_verified")
        validate_network_boundary(server=self.server)

    def execution_metadata(self) -> dict[str, Any]:
        self.validate()
        return {
            "executor": WINDOWS_NATIVE_EXECUTOR,
            "executor_id": self.executor_id,
            "server_id": self.server.server_id,
            "brain_id": self.server.brain_id,
            "network_generation": self.server.network_generation,
            "brain_generation": self.brain_generation,
            "fencing_token": self.fencing_token,
            "authority_policy_version": self.authority_policy_version,
            "contract_status": self.state,
        }
