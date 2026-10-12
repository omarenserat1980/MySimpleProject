"""Evidence-aware metadata and deterministic timing primitives for virtual hardware.

These profiles describe simulator behavior; they do not claim electrical or cycle-level
equivalence to physical hardware. Vendor-specific profiles must cite authoritative sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class FidelityLevel(str, Enum):
    FUNCTIONAL = "functional"
    TIMING_MODEL = "timing_model"
    CYCLE_ACCURATE = "cycle_accurate"
    PERFORMANCE_ESTIMATION = "performance_estimation"


class ProvenanceKind(str, Enum):
    VENDOR_DOCUMENTATION = "vendor_documentation"
    MEASURED_HARDWARE = "measured_hardware"
    DERIVED = "derived"
    SYNTHETIC_BASELINE = "synthetic_baseline"


@dataclass(frozen=True)
class SpecificationSource:
    kind: ProvenanceKind
    reference: str
    note: str = ""

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("PROFILE_SOURCE_REFERENCE_REQUIRED")


@dataclass(frozen=True)
class HardwareProfile:
    profile_id: str
    category: str
    model: str
    fidelity: FidelityLevel
    parameters: Mapping[str, int | float | str | bool] = field(default_factory=dict)
    modeled_behaviors: tuple[str, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    sources: tuple[SpecificationSource, ...] = ()
    conformance_tests: tuple[str, ...] = ()
    units: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("profile_id", "category", "model"):
            if not getattr(self, name).strip():
                raise ValueError(f"PROFILE_{name.upper()}_REQUIRED")
        if not self.sources:
            raise ValueError("PROFILE_PROVENANCE_REQUIRED")
        if not self.modeled_behaviors:
            raise ValueError("PROFILE_MODELED_BEHAVIORS_REQUIRED")
        if not self.conformance_tests:
            raise ValueError("PROFILE_CONFORMANCE_TESTS_REQUIRED")

    def describe(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "category": self.category,
            "model": self.model,
            "fidelity": self.fidelity.value,
            "parameters": dict(self.parameters),
            "units": dict(self.units),
            "modeled_behaviors": list(self.modeled_behaviors),
            "unsupported_features": list(self.unsupported_features),
            "sources": [
                {"kind": source.kind.value, "reference": source.reference, "note": source.note}
                for source in self.sources
            ],
            "conformance_tests": list(self.conformance_tests),
        }


@dataclass(frozen=True)
class ClockModel:
    """Deterministic ideal clock; not a wall-clock or physical oscillator simulation."""

    frequency_hz: float
    name: str = "ideal"

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0:
            raise ValueError("CLOCK_FREQUENCY_MUST_BE_POSITIVE")

    def cycles_to_seconds(self, cycles: int) -> float:
        if cycles < 0:
            raise ValueError("CLOCK_CYCLES_MUST_NOT_BE_NEGATIVE")
        return cycles / self.frequency_hz

    def seconds_to_cycles(self, seconds: float) -> int:
        if seconds < 0:
            raise ValueError("CLOCK_SECONDS_MUST_NOT_BE_NEGATIVE")
        # Round up: a modeled operation must consume enough whole cycles.
        import math
        return math.ceil(seconds * self.frequency_hz)


@dataclass(frozen=True)
class MachineManifest:
    """Versioned component inventory for a virtual machine profile."""

    machine_id: str
    schema_version: int
    components: tuple[HardwareProfile, ...]
    required_categories: tuple[str, ...] = ("cpu", "memory", "bus", "storage", "network")

    def validate(self) -> dict:
        errors: list[str] = []
        if not self.machine_id.strip():
            errors.append("MACHINE_ID_REQUIRED")
        if self.schema_version < 1:
            errors.append("SCHEMA_VERSION_MUST_BE_POSITIVE")
        ids = [component.profile_id for component in self.components]
        if len(ids) != len(set(ids)):
            errors.append("DUPLICATE_COMPONENT_PROFILE_ID")
        categories = {component.category for component in self.components}
        missing = sorted(set(self.required_categories) - categories)
        if missing:
            errors.append("MISSING_REQUIRED_CATEGORIES:" + ",".join(missing))
        return {
            "ok": not errors,
            "machine_id": self.machine_id,
            "schema_version": self.schema_version,
            "component_count": len(self.components),
            "categories": sorted(categories),
            "missing_categories": missing,
            "errors": errors,
            "fidelity": {
                level.value: sum(component.fidelity == level for component in self.components)
                for level in FidelityLevel
            },
            "host_resources_created": False,
            "claim": "profile validation only; no physical hardware equivalence is implied",
        }

    def describe(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "schema_version": self.schema_version,
            "validation": self.validate(),
            "components": [component.describe() for component in self.components],
        }


def synthetic_baseline_profiles() -> tuple[HardwareProfile, ...]:
    """Return explicitly synthetic starter profiles, not vendor-specific specifications."""
    source = SpecificationSource(
        ProvenanceKind.SYNTHETIC_BASELINE,
        "brain://virtual-hardware/baseline-v1",
        "Software test baseline; replace with sourced vendor parameters for real-device comparison.",
    )
    return (
        HardwareProfile(
            "brain-cpu-functional-v1", "cpu", "Brain educational 8-register ISA",
            FidelityLevel.FUNCTIONAL,
            {"register_count": 8, "default_clock_hz": 1_000_000},
            ("MOVI", "ADD", "SUB", "LOAD", "STORE", "JMP", "JZ", "OUT", "HALT"),
            ("x86-64", "AArch64", "speculative execution", "physical cache timing"),
            (source,), ("cpu_instruction_vectors", "cpu_illegal_opcode", "cpu_cycle_limit"),
        ),
        HardwareProfile(
            "brain-memory-functional-v1", "memory", "Brain addressable-cell RAM",
            FidelityLevel.FUNCTIONAL,
            {"default_addressable_cells": 65536, "cell_model": "integer-valued addressable cell"},
            ("address bounds", "read/write", "snapshot/restore"),
            ("DDR channel timing", "refresh timing", "ECC fault model", "NUMA"),
            (source,), ("ram_bounds", "ram_snapshot_roundtrip", "ram_restore_size_mismatch"),
        ),
        HardwareProfile(
            "brain-bus-functional-v1", "bus", "Brain deterministic device registry",
            FidelityLevel.FUNCTIONAL,
            {},
            ("device attach", "duplicate-name rejection", "interrupt event recording"),
            ("PCIe transaction timing", "electrical signaling", "IOMMU enforcement"),
            (source,), ("bus_attach", "bus_duplicate_attach", "bus_interrupt_recording"),
        ),
        HardwareProfile(
            "brain-storage-functional-v1", "storage", "Brain in-memory virtual storage",
            FidelityLevel.FUNCTIONAL,
            {"default_capacity_bytes": 1048576},
            ("capacity enforcement", "byte read/write", "SHA-256 manifest"),
            ("NVMe queues", "physical SSD latency", "TRIM", "SMART telemetry", "power-loss durability"),
            (source,), ("storage_capacity", "storage_read_write", "storage_manifest_hash"),
        ),
        HardwareProfile(
            "brain-network-functional-v1", "network", "Brain packet-buffer NIC",
            FidelityLevel.FUNCTIONAL,
            {"default_link_mbps": 1000},
            ("packet injection", "packet send buffer", "FIFO receive"),
            ("Ethernet PHY", "wire timing", "congestion control", "interrupt moderation"),
            (source,), ("nic_send_receive", "nic_fifo_order"),
        ),
        HardwareProfile(
            "brain-gpu-framebuffer-v1", "gpu", "Brain software framebuffer",
            FidelityLevel.FUNCTIONAL,
            {"default_width": 320, "default_height": 200},
            ("framebuffer clear", "pixel bounds", "pixel write"),
            ("CUDA", "Vulkan", "DirectX", "parallel shader execution", "GPU performance equivalence"),
            (source,), ("gpu_pixel_bounds", "gpu_clear"),
        ),
    )
