"""Fail-closed contract for a physical/native Windows Server executor."""
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
    attestation: dict[str, Any]
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

        if not isinstance(self.attestation, dict):
            raise ValueError("windows_native_attestation_record_required")
        if self.attestation.get("verified") is not True:
            raise ValueError("windows_native_attestation_not_verified")
        if not str(self.attestation.get("attestation_digest", "")).strip():
            raise ValueError("windows_native_attestation_digest_required")
        if not str(self.attestation.get("challenge", "")).strip():
            raise ValueError("windows_native_attestation_challenge_required")
        if self.attestation.get("replay_protected") is not True:
            raise ValueError("windows_native_attestation_replay_protection_required")
        if self.attestation.get("executor_id") != self.executor_id:
            raise ValueError("windows_native_attestation_executor_mismatch")
        if self.attestation.get("server_id") != self.server.server_id:
            raise ValueError("windows_native_attestation_server_mismatch")
        if int(self.attestation.get("brain_generation", 0)) != self.brain_generation:
            raise ValueError("windows_native_attestation_generation_mismatch")
        if int(self.attestation.get("network_generation", 0)) != self.server.network_generation:
            raise ValueError("windows_native_attestation_network_generation_mismatch")

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
            "attestation_digest": self.attestation["attestation_digest"],
        }
