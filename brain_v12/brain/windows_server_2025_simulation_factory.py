"""Windows Server 2025 behavior simulator for Electronic Brain.

SIMULATION ONLY: this module never launches a VM, invokes QEMU/Hyper-V, accesses a
cloud API, downloads media, or contacts a host. It models boot-state transitions
and emits hash-chained synthetic evidence. A successful result is not a real OS boot.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .windows_server_2025_simulation_progress import simulation_progress_snapshot

SCHEMA = "electronic-brain.windows-server-2025-simulation.v1"
SIMULATED_CAPABILITY = "windows-server-2025-simulated-boot"
REAL_CAPABILITIES = {"windows-server-2025-real-boot", "windows-server-2025-cloud-native"}

STAGES = (
    "CREATED", "PREFLIGHT", "SIMULATOR_SELECTED", "VIRTUAL_HARDWARE_READY",
    "FIRMWARE_CHECK", "VIRTUAL_DISK_CHECK", "BOOT_CONFIGURATION_CHECK",
    "BOOT_MANAGER_SIMULATION", "KERNEL_PHASE_SIMULATION",
    "DRIVER_PHASE_SIMULATION", "SERVICE_INITIALIZATION",
    "NETWORK_INITIALIZATION", "HEALTH_CHECK", "SIMULATED_BOOT_COMPLETE",
)
TERMINAL = {
    "SIMULATED_BOOT_COMPLETE", "SIMULATED_BOOT_PARTIAL",
    "SIMULATED_BOOT_FAILED", "BLOCKED", "CANCELLED",
}
SCENARIOS = {
    "success", "no_boot_disk", "invalid_boot_config", "low_disk_space",
    "service_failure", "missing_dependency", "dns_failure", "network_down",
    "out_of_memory", "cancel_during_boot", "restart", "power_loss_recovery",
    "stage_crash", "corrupt_evidence", "duplicate_request", "timeout",
    "driver_failure", "verification_failure", "invalid_executor_pointer",
    "real_executor_route",
}
FAILURE_STAGE = {
    "no_boot_disk": ("VIRTUAL_DISK_CHECK", "NO_BOOT_DISK"),
    "invalid_boot_config": ("BOOT_CONFIGURATION_CHECK", "INVALID_BOOT_CONFIGURATION"),
    "low_disk_space": ("VIRTUAL_DISK_CHECK", "INSUFFICIENT_VIRTUAL_DISK"),
    "service_failure": ("SERVICE_INITIALIZATION", "SIMULATED_SERVICE_FAILED"),
    "missing_dependency": ("SERVICE_INITIALIZATION", "SERVICE_DEPENDENCY_MISSING"),
    "dns_failure": ("NETWORK_INITIALIZATION", "SIMULATED_DNS_FAILED"),
    "network_down": ("NETWORK_INITIALIZATION", "SIMULATED_NETWORK_DOWN"),
    "out_of_memory": ("VIRTUAL_HARDWARE_READY", "SIMULATED_OUT_OF_MEMORY"),
    "cancel_during_boot": ("BOOT_MANAGER_SIMULATION", "SIMULATION_CANCELLED"),
    "stage_crash": ("KERNEL_PHASE_SIMULATION", "SIMULATED_STAGE_CRASH"),
    "power_loss_recovery": ("BOOT_MANAGER_SIMULATION", "POWER_LOSS_INJECTED"),
    "timeout": ("DRIVER_PHASE_SIMULATION", "SIMULATED_TIMEOUT"),
    "driver_failure": ("DRIVER_PHASE_SIMULATION", "SIMULATED_DRIVER_FAILED"),
    "duplicate_request": ("PREFLIGHT", "DUPLICATE_REQUEST_REJECTED"),
    "invalid_executor_pointer": ("PREFLIGHT", "INVALID_EXECUTOR_POINTER"),
    "real_executor_route": ("PREFLIGHT", "REAL_EXECUTOR_ROUTE_BLOCKED"),
    "verification_failure": ("HEALTH_CHECK", "VERIFICATION_GATE_FAILED"),
}


@dataclass(frozen=True)
class VirtualHardwareModel:
    vcpu_count: int = 2
    ram_mib: int = 4096
    disk_gib: int = 64
    disk_free_gib: int = 48
    network_attached: bool = True
    dns_available: bool = True
    firmware_version: str = "BRAIN-UEFI-MODEL-1"
    boot_disk_present: bool = True
    boot_config_valid: bool = True

    def validate(self) -> list[str]:
        errors = []
        numeric_fields = {
            "vcpu_count": self.vcpu_count,
            "ram_mib": self.ram_mib,
            "disk_gib": self.disk_gib,
            "disk_free_gib": self.disk_free_gib,
        }
        for name, value in numeric_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(name.upper() + "_MUST_BE_INTEGER")
        for name, value in {
            "network_attached": self.network_attached,
            "dns_available": self.dns_available,
            "boot_disk_present": self.boot_disk_present,
            "boot_config_valid": self.boot_config_valid,
        }.items():
            if not isinstance(value, bool):
                errors.append(name.upper() + "_MUST_BE_BOOLEAN")
        if isinstance(self.vcpu_count, int) and not isinstance(self.vcpu_count, bool) and not 1 <= self.vcpu_count <= 256:
            errors.append("VCPU_COUNT_OUT_OF_RANGE")
        if isinstance(self.ram_mib, int) and not isinstance(self.ram_mib, bool) and not 512 <= self.ram_mib <= 1_048_576:
            errors.append("RAM_MIB_OUT_OF_RANGE")
        if isinstance(self.disk_gib, int) and not isinstance(self.disk_gib, bool) and not 1 <= self.disk_gib <= 65_536:
            errors.append("DISK_GIB_OUT_OF_RANGE")
        if isinstance(self.disk_free_gib, int) and not isinstance(self.disk_free_gib, bool):
            if not isinstance(self.disk_gib, int) or isinstance(self.disk_gib, bool) or not 0 <= self.disk_free_gib <= self.disk_gib:
                errors.append("DISK_FREE_SPACE_INVALID")
        if not isinstance(self.firmware_version, str) or not self.firmware_version.strip():
            errors.append("FIRMWARE_VERSION_REQUIRED")
        return errors


class EvidenceRecorder:
    """Append-only in-memory hash chain for a single simulation run."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, stage: str, status: str, reason_code: str | None = None,
               details: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {
            "event_id": str(uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "status": status,
            "reason_code": reason_code,
            "evidence_type": "SYNTHETIC_SIMULATION_EVENT",
            "details": details or {},
            "previous_hash": self.events[-1]["evidence_hash"] if self.events else None,
        }
        body["evidence_hash"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.events.append(body)
        return body

    @staticmethod
    def verify(events: list[dict[str, Any]]) -> dict[str, Any]:
        previous = None
        for index, event in enumerate(events):
            body = {key: value for key, value in event.items() if key != "evidence_hash"}
            expected = hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if event.get("previous_hash") != previous or event.get("evidence_hash") != expected:
                return {"ok": False, "status": "VERIFICATION_FAILED",
                        "failed_event_index": index, "reason": "EVIDENCE_CHAIN_INVALID"}
            previous = event["evidence_hash"]
        return {"ok": True, "status": "VERIFIED_SYNTHETIC_EVIDENCE",
                "event_count": len(events), "final_hash": previous}


@dataclass
class WindowsServer2025Simulator:
    hardware: VirtualHardwareModel = field(default_factory=VirtualHardwareModel)
    simulator_version: str = "2.0.0"

    def run(self, scenario_id: str = "success", *,
            capability: str = SIMULATED_CAPABILITY) -> dict[str, Any]:
        run_id = str(uuid4())
        recorder = EvidenceRecorder()
        started = datetime.now(timezone.utc)
        if scenario_id not in SCENARIOS:
            return self._blocked(run_id, scenario_id, "UNKNOWN_SCENARIO")
        if capability in REAL_CAPABILITIES or capability != SIMULATED_CAPABILITY:
            return self._blocked(run_id, scenario_id, "SIMULATION_CAPABILITY_MISMATCH")
        errors = self.hardware.validate()
        if errors:
            recorder.record("PREFLIGHT", "FAILED", "INVALID_VIRTUAL_HARDWARE",
                            {"errors": errors})
            return self._report(run_id, scenario_id, "SIMULATED_BOOT_FAILED",
                                recorder, started, errors[0])
        recorder.record("CREATED", "PASS", details={"schema": SCHEMA})
        preflight_failures = {
            "duplicate_request": "DUPLICATE_REQUEST_REJECTED",
            "invalid_executor_pointer": "INVALID_EXECUTOR_POINTER",
            "real_executor_route": "REAL_EXECUTOR_ROUTE_BLOCKED",
        }
        if scenario_id in preflight_failures:
            reason = preflight_failures[scenario_id]
            recorder.record("PREFLIGHT", "BLOCKED", reason,
                            {"execution_mode": "SIMULATION_ONLY"})
            return self._report(run_id, scenario_id, "BLOCKED", recorder, started, reason)
        recorder.record("PREFLIGHT", "PASS", details={
            "execution_mode": "SIMULATION_ONLY",
            "side_effects_performed": False,
            "external_resources_created": False,
        })
        recorder.record("SIMULATOR_SELECTED", "PASS", details={
            "simulator_id": "windows-server-2025-behavior-model",
            "simulator_version": self.simulator_version,
        })
        failure = FAILURE_STAGE.get(scenario_id)
        if failure is None:
            if not self.hardware.boot_disk_present:
                failure = ("VIRTUAL_DISK_CHECK", "NO_BOOT_DISK")
            elif not self.hardware.boot_config_valid:
                failure = ("BOOT_CONFIGURATION_CHECK", "INVALID_BOOT_CONFIGURATION")
            elif self.hardware.disk_gib < 32 or self.hardware.disk_free_gib < 8:
                failure = ("VIRTUAL_DISK_CHECK", "INSUFFICIENT_VIRTUAL_DISK")
            elif self.hardware.ram_mib < 2048:
                failure = ("VIRTUAL_HARDWARE_READY", "INSUFFICIENT_VIRTUAL_RAM")
            elif not self.hardware.network_attached:
                failure = ("NETWORK_INITIALIZATION", "SIMULATED_NETWORK_DOWN")
            elif not self.hardware.dns_available:
                failure = ("NETWORK_INITIALIZATION", "SIMULATED_DNS_FAILED")
        recovery_status = None
        stages = list(STAGES[3:-1])
        for stage in stages:
            if scenario_id == "out_of_memory" and stage == "VIRTUAL_HARDWARE_READY":
                reason = "SIMULATED_OUT_OF_MEMORY"
            elif failure and stage == failure[0]:
                reason = failure[1]
            else:
                reason = None
            if reason:
                status = "CANCELLED" if scenario_id == "cancel_during_boot" else "FAILED"
                recorder.record(stage, status, reason, {"scenario_id": scenario_id})
                if scenario_id == "power_loss_recovery":
                    recovery_status = "SIMULATED_RECOVERY_PASS"
                    recorder.record("RECOVERY_IN_PROGRESS", "PASS",
                                    details={"recovery_mode": "STATE_MODEL_ONLY"})
                    recorder.record(stage, "PASS",
                                    details={"recovered_after": reason,
                                             "recovery_mode": "STATE_MODEL_ONLY"})
                    continue
                final = "CANCELLED" if status == "CANCELLED" else "SIMULATED_BOOT_FAILED"
                if scenario_id == "verification_failure":
                    final = "SIMULATED_BOOT_FAILED"
                return self._report(run_id, scenario_id, final, recorder, started, reason)
            recorder.record(stage, "PASS", details=self._stage_details(stage, scenario_id))
            if scenario_id == "restart" and stage == "BOOT_MANAGER_SIMULATION":
                recorder.record("RESTART_SIMULATION", "PASS",
                                details={"restart_kind": "logical_only"})
        if scenario_id == "corrupt_evidence":
            recorder.events[-1]["details"]["tampered_for_test"] = True
            verification = EvidenceRecorder.verify(recorder.events)
        else:
            verification = EvidenceRecorder.verify(recorder.events)
        if scenario_id == "verification_failure" or not verification["ok"]:
            return self._report(run_id, scenario_id, "SIMULATED_BOOT_FAILED",
                                recorder, started,
                                "EVIDENCE_CHAIN_INVALID" if not verification["ok"] else "VERIFICATION_GATE_FAILED",
                                verification=verification)
        recorder.record("SIMULATED_BOOT_COMPLETE", "PASS",
                        details={"real_windows_boot_verified": False})
        verification = EvidenceRecorder.verify(recorder.events)
        return self._report(run_id, scenario_id, "SIMULATED_BOOT_SUCCESS",
                            recorder, started, verification=verification,
                            recovery=recovery_status)

    def _stage_details(self, stage: str, scenario_id: str) -> dict[str, Any]:
        details: dict[str, Any] = {"scenario_id": scenario_id}
        if stage == "VIRTUAL_HARDWARE_READY":
            details["simulated_resources"] = asdict(self.hardware)
        elif stage == "FIRMWARE_CHECK":
            details["firmware_model"] = self.hardware.firmware_version
        elif stage == "VIRTUAL_DISK_CHECK":
            details["disk"] = {"present": self.hardware.boot_disk_present,
                               "capacity_gib": self.hardware.disk_gib,
                               "free_gib": self.hardware.disk_free_gib}
        elif stage == "BOOT_CONFIGURATION_CHECK":
            details["boot_config_valid"] = self.hardware.boot_config_valid
        elif stage == "SERVICE_INITIALIZATION":
            details["services"] = [
                {"name": "EventLog", "state": "RUNNING"},
                {"name": "NetworkProfile", "state": "RUNNING"},
                {"name": "BrainSimHealth", "state": "RUNNING"},
            ]
        elif stage == "NETWORK_INITIALIZATION":
            details["network"] = {"attached": self.hardware.network_attached,
                                  "dns_available": self.hardware.dns_available}
        elif stage in {"BOOT_MANAGER_SIMULATION", "KERNEL_PHASE_SIMULATION",
                       "DRIVER_PHASE_SIMULATION"}:
            details["operation"] = "logical_behavior_model_only"
        return details

    def _blocked(self, run_id: str, scenario_id: str, reason: str) -> dict[str, Any]:
        recorder = EvidenceRecorder()
        recorder.record("BLOCKED", "BLOCKED", reason)
        return self._report(run_id, scenario_id, "BLOCKED", recorder,
                            datetime.now(timezone.utc), reason)

    def _report(self, run_id: str, scenario_id: str, status: str,
                recorder: EvidenceRecorder, started: datetime, reason: str | None = None,
                *, verification: dict[str, Any] | None = None,
                recovery: str | None = None) -> dict[str, Any]:
        ended = datetime.now(timezone.utc)
        verification = verification or EvidenceRecorder.verify(recorder.events)
        return {
            "schema": SCHEMA,
            "implementation_progress": simulation_progress_snapshot(),
            "run_id": run_id,
            "scenario_id": scenario_id,
            "simulator_id": "windows-server-2025-behavior-model",
            "simulator_version": self.simulator_version,
            "capability": SIMULATED_CAPABILITY,
            "execution_mode": "SIMULATION_ONLY",
            "status": status,
            "reason_code": reason,
            "started_at_utc": started.isoformat(),
            "finished_at_utc": ended.isoformat(),
            "duration_ms": max(0, int((ended - started).total_seconds() * 1000)),
            "simulated_resources": asdict(self.hardware),
            "host_observed_resources": {"status": "NOT_COLLECTED", "values": None},
            "events": recorder.events,
            "verification": verification,
            "recovery_status": recovery or "NOT_REQUESTED",
            "side_effects_performed": False,
            "external_resources_created": False,
            "real_windows_boot_verified": False,
        }


def simulate_windows_server_2025(scenario_id: str = "success",
                                 hardware: VirtualHardwareModel | None = None,
                                 *, capability: str = SIMULATED_CAPABILITY) -> dict[str, Any]:
    """Public convenience function; performs simulation only."""
    return WindowsServer2025Simulator(hardware or VirtualHardwareModel()).run(
        scenario_id, capability=capability
    )


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a human-readable report without upgrading synthetic evidence."""
    verification = report.get("verification") or {}
    lines = [
        "# Windows Server 2025 Simulation Report",
        "",
        f"- Run ID: {report.get('run_id', 'unknown')}",
        f"- Status: {report.get('status', 'UNKNOWN')}",
        f"- Scenario: {report.get('scenario_id', 'unknown')}",
        f"- Simulator: {report.get('simulator_id', 'unknown')}@{report.get('simulator_version', 'unknown')}",
        "- Execution mode: SIMULATION_ONLY",
        f"- Simulation implementation progress: {(report.get('implementation_progress') or {}).get('percent', 0)}% (weighted roadmap coverage)",
        "- Progress is not a boot probability or real Windows boot evidence.",
        "- Real Windows boot verified: false",
        f"- Evidence verification: {verification.get('status', 'NOT_CHECKED')}",
        f"- Recovery status: {report.get('recovery_status', 'NOT_REQUESTED')}",
        "",
        "## Modeled resources",
        "",
        "~~~json",
        json.dumps(report.get("simulated_resources", {}), indent=2, sort_keys=True),
        "~~~",
        "",
        "## Events",
        "",
        "| Stage | Status | Reason | Evidence hash |",
        "|---|---|---|---|",
    ]
    for event in report.get("events", []):
        stage = str(event.get("stage", "")).replace("|", "\\|")
        status = str(event.get("status", "")).replace("|", "\\|")
        reason = str(event.get("reason_code") or "—").replace("|", "\\|")
        digest = str(event.get("evidence_hash", "")).replace("|", "\\|")
        lines.append(f"| {stage} | {status} | {reason} | {digest} |")
    lines.extend([
        "",
        "> This report contains synthetic model events only. It is not evidence that Windows Server 2025 booted on real hardware or in a real VM.",
        "",
    ])
    return "\n".join(lines)
