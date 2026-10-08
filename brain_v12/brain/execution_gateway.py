"""Canonical Brain-owned execution gateway.

This is the only runtime authority for production execution. GitHub, CI, and
device adapters are control/evidence integrations; they are never implicit
executors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .execution_policy import BRAIN_INTERNAL, WINDOWS_REAL_BOOT, Executor, choose_executor
from .internal_runner import InternalRunner
from .windows_cloud_executor import CloudWindowsVM, WindowsCloudExecutor


@dataclass(frozen=True)
class ExecutionDecision:
    executor: str
    capability: str
    verified: bool
    reason: str


class BrainExecutionGateway:
    """Fail-closed authority for Brain-owned execution."""

    def __init__(self, runner: InternalRunner | None = None) -> None:
        self.runner = runner or InternalRunner()

    def authorize_windows_cloud(
        self,
        vm: CloudWindowsVM,
        node: dict[str, Any],
        *,
        heartbeat_timeout: float = 120.0,
        now: float | None = None,
    ) -> ExecutionDecision:
        """Authorize Windows Cloud only after fresh guest-runtime proof.

        Infrastructure RUNNING state alone is insufficient. This path is the
        explicit runtime exception to the internal-only default and never
        falls back to GitHub CI or another external executor.
        """
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
            capability=WINDOWS_REAL_BOOT,
            verified=True,
            reason="WINDOWS_CLOUD_RUNTIME_VERIFIED",
        )

    def authorize_task(
        self,
        capability: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionDecision:
        """Authorize a task using its explicit runtime contract.

        Windows real-boot tasks must carry a verified Windows Cloud VM/node
        contract. They are never silently executed by the local runner.
        """
        metadata = metadata or {}
        if capability == WINDOWS_REAL_BOOT:
            executor_type = str(metadata.get("executor", "")).strip().lower()
            # QEMU real-boot is a distinct capability from a native cloud
            # Windows VM. A native provider VM cannot satisfy this contract.
            if executor_type != "windows-real-boot-qemu":
                raise RuntimeError("WINDOWS_REAL_BOOT_REQUIRES_QEMU_CLOUD_EXECUTOR")
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
        # Production execution is Brain-owned. External executors are not
        # considered candidates for runtime work.
        internal = Executor(
            name=BRAIN_INTERNAL,
            capabilities=frozenset({
                "brain-internal-execution",
                WINDOWS_REAL_BOOT,
                "qemu",
            }),
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
