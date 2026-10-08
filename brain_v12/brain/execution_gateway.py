"""Canonical Brain-owned execution gateway.

This is the only runtime authority for production execution. GitHub, CI, and
device adapters are control/evidence integrations; they are never implicit
executors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .execution_policy import (
    BRAIN_INTERNAL,
    WINDOWS_CLOUD,
    WINDOWS_CLOUD_NATIVE,
    WINDOWS_REAL_BOOT,
    WINDOWS_NATIVE_EXECUTOR,
    Executor,
    choose_executor,
)
from .internal_runner import InternalRunner
from .windows_cloud_executor import CloudWindowsVM, WindowsCloudExecutor
from .windows_native_executor import WindowsNativeExecutorContract
from .windows_native_enrollment import VerifiedAttestationRegistry
from .windows_server_network_contract import (
    NetworkZone,
    NodeTrustState,
    WindowsServerNetworkContract,
)


@dataclass(frozen=True)
class ExecutionDecision:
    executor: str
    capability: str
    verified: bool
    reason: str


def _native_contract_from_metadata(metadata: dict[str, Any]) -> WindowsNativeExecutorContract:
    raw = metadata.get("native_contract")
    if not isinstance(raw, dict):
        raise RuntimeError("WINDOWS_NATIVE_EXECUTION_CONTRACT_REQUIRED")
    server_raw = raw.get("server")
    if not isinstance(server_raw, dict):
        raise RuntimeError("WINDOWS_NATIVE_SERVER_CONTRACT_REQUIRED")

    def zone(value: Any, default: NetworkZone) -> NetworkZone:
        try:
            return NetworkZone(str(value))
        except ValueError:
            return default

    try:
        state = NodeTrustState(str(server_raw.get("state", "")))
    except ValueError as exc:
        raise RuntimeError("WINDOWS_NATIVE_SERVER_STATE_INVALID") from exc

    server = WindowsServerNetworkContract(
        server_id=str(server_raw.get("server_id", "")),
        brain_id=str(server_raw.get("brain_id", "")),
        network_generation=int(server_raw.get("network_generation", 0)),
        management_zone=zone(server_raw.get("management_zone"), NetworkZone.MANAGEMENT),
        client_zone=zone(server_raw.get("client_zone"), NetworkZone.CLIENT),
        service_zone=zone(server_raw.get("service_zone"), NetworkZone.SERVICE),
        internet_zone=zone(server_raw.get("internet_zone"), NetworkZone.INTERNET),
        state=state,
        capabilities=frozenset(server_raw.get("capabilities", [])),
        client_ids=frozenset(server_raw.get("client_ids", [])),
        fencing_token=server_raw.get("fencing_token"),
        attestation_verified=bool(server_raw.get("attestation_verified", False)),
        firewall_policy_version=str(server_raw.get("firewall_policy_version", "")),
        metadata=server_raw.get("metadata", {}),
    )
    return WindowsNativeExecutorContract(
        executor_id=str(raw.get("executor_id", "")),
        server=server,
        attestation=raw.get("attestation"),
        brain_generation=int(raw.get("brain_generation", 0)),
        fencing_token=int(raw.get("fencing_token", 0)),
        authority_policy_version=str(raw.get("authority_policy_version", "authority-policy-v1")),
        state=str(raw.get("state", "VERIFIED")),
    )


class BrainExecutionGateway:
    """Fail-closed authority for Brain-owned execution."""

    def __init__(self, runner: InternalRunner | None = None, attestation_registry: VerifiedAttestationRegistry | None = None) -> None:
        self.runner = runner or InternalRunner()
        self.attestation_registry = attestation_registry or VerifiedAttestationRegistry()

    def authorize_windows_cloud(
        self,
        vm: CloudWindowsVM,
        node: dict[str, Any],
        *,
        heartbeat_timeout: float = 120.0,
        now: float | None = None,
    ) -> ExecutionDecision:
        verification = WindowsCloudExecutor().verify_runtime(
            vm,
            node,
            heartbeat_timeout=heartbeat_timeout,
            now=now,
        )
        if not verification.get("runtime_verified"):
            raise RuntimeError(
                "WINDOWS_CLOUD_RUNTIME_NOT_VERIFIED:"
                + str(verification.get("reason", "UNKNOWN"))
            )
        return ExecutionDecision(
            executor="windows-server-2025-cloud",
            capability=WINDOWS_CLOUD_NATIVE,
            verified=True,
            reason="WINDOWS_CLOUD_NATIVE_RUNTIME_VERIFIED",
        )

    def authorize_task(
        self,
        capability: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionDecision:
        metadata = metadata or {}
        if capability == WINDOWS_NATIVE_EXECUTOR:
            contract = _native_contract_from_metadata(metadata)
            digest = str((contract.attestation or {}).get("attestation_digest", "")).strip()
            trusted = self.attestation_registry.get(digest)
            if trusted is None:
                raise RuntimeError("WINDOWS_NATIVE_ATTESTATION_NOT_REGISTERED")
            contract = WindowsNativeExecutorContract(
                executor_id=contract.executor_id,
                server=contract.server,
                attestation=trusted,
                brain_generation=contract.brain_generation,
                fencing_token=contract.fencing_token,
                authority_policy_version=contract.authority_policy_version,
                state=contract.state,
            )
            contract.validate()
            return ExecutionDecision(
                executor=WINDOWS_NATIVE_EXECUTOR,
                capability=WINDOWS_NATIVE_EXECUTOR,
                verified=True,
                reason="WINDOWS_NATIVE_EXECUTOR_CONTRACT_VERIFIED",
            )
        if capability == WINDOWS_REAL_BOOT:
            executor_type = str(metadata.get("executor", "")).strip().lower()
            if executor_type != "windows-real-boot-qemu":
                raise RuntimeError("WINDOWS_REAL_BOOT_REQUIRES_QEMU_CLOUD_EXECUTOR")
            raise RuntimeError("WINDOWS_REAL_BOOT_QEMU_RUNTIME_ADAPTER_NOT_CONFIGURED")
        if capability == WINDOWS_CLOUD_NATIVE:
            executor_type = str(metadata.get("executor", "")).strip().lower()
            if executor_type != WINDOWS_CLOUD:
                raise RuntimeError("WINDOWS_CLOUD_NATIVE_REQUIRES_NATIVE_CLOUD_EXECUTOR")
            vm_data = metadata.get("vm")
            node = metadata.get("node")
            if not isinstance(vm_data, dict) or not isinstance(node, dict):
                raise RuntimeError("WINDOWS_CLOUD_RUNTIME_EVIDENCE_REQUIRED")
            vm = CloudWindowsVM(
                vm_id=str(vm_data.get("vm_id", "")),
                provider=str(vm_data.get("provider", "")),
                region=str(vm_data.get("region", "")),
                state=str(vm_data.get("state", "")),
                os=str(vm_data.get("os", "Windows Server 2025")),
                architecture=str(vm_data.get("architecture", "x86_64")),
                metadata=vm_data.get("metadata", {}),
            )
            return self.authorize_windows_cloud(
                vm,
                node,
                heartbeat_timeout=float(metadata.get("heartbeat_timeout", 120.0)),
                now=metadata.get("now"),
            )
        return self.authorize(capability)

    def authorize(self, capability: str) -> ExecutionDecision:
        internal = Executor(
            name=BRAIN_INTERNAL,
            capabilities=frozenset({"brain-internal-execution", "qemu"}),
            priority=0,
            external=False,
        )
        selected = choose_executor((internal,), capability)
        self.runner.require(capability)
        return ExecutionDecision(
            executor=selected.name,
            capability=capability,
            verified=True,
            reason="BRAIN_INTERNAL_AUTHORITY",
        )

    def run(self, argv: list[str], capability: str = "brain-internal-execution",
            cwd: str | None = None, timeout: int | None = None) -> dict[str, Any]:
        decision = self.authorize(capability)
        result = self.runner.run(argv, cwd=cwd, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "executor": decision.executor,
            "authority": "brain-internal",
            "capability": capability,
            "verified_executor": decision.verified,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
