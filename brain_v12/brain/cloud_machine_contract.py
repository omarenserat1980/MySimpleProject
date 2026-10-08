"""Brain Cloud Machine acceptance gate.

The cloud machine is accepted only when its declared resources and runtime
capabilities satisfy the Brain contract. This gate is deliberately independent
of Windows so the host can be validated before any guest boot is attempted.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class CloudMachineContract:
    schema: str
    machine_id: str
    architecture: str
    vcpu: int
    ram_mb: int
    storage_gb: int
    network: bool
    virtualization: bool
    uefi: bool
    qemu: bool
    ovmf: bool
    evidence_id: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


REQUIRED_SCHEMA = "brain.cloud-machine-contract.v1"


def accept(contract: CloudMachineContract) -> dict[str, Any]:
    """Fail closed if the cloud host cannot support the Brain runtime."""

    failures: list[str] = []

    if contract.schema != REQUIRED_SCHEMA:
        failures.append("SCHEMA_INVALID")
    if not contract.machine_id.strip():
        failures.append("MACHINE_ID_REQUIRED")
    if contract.architecture.lower() not in {"x86_64", "amd64"}:
        failures.append("ARCHITECTURE_UNSUPPORTED")
    if contract.vcpu < 2:
        failures.append("VCPU_INSUFFICIENT")
    if contract.ram_mb < 4096:
        failures.append("RAM_INSUFFICIENT")
    if contract.storage_gb < 80:
        failures.append("STORAGE_INSUFFICIENT")
    if not contract.network:
        failures.append("NETWORK_UNAVAILABLE")
    if not contract.virtualization:
        failures.append("VIRTUALIZATION_UNAVAILABLE")
    if not contract.uefi:
        failures.append("UEFI_UNAVAILABLE")
    if not contract.qemu:
        failures.append("QEMU_UNAVAILABLE")
    if not contract.ovmf:
        failures.append("OVMF_UNAVAILABLE")
    if not contract.evidence_id.strip():
        failures.append("EVIDENCE_ID_REQUIRED")

    accepted = not failures
    return {
        "accepted": accepted,
        "status": "CLOUD_MACHINE_ACCEPTED" if accepted else "CLOUD_MACHINE_REJECTED",
        "machine_id": contract.machine_id,
        "failures": failures,
        "contract": contract.as_dict(),
    }
