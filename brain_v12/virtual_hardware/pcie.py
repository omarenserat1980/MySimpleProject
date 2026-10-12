"""Deterministic transaction-level PCIe model for Brain's software-defined bus.

This models endpoint discovery, basic configuration space, BAR/MMIO access, completion
status, bounded traces, and deterministic injected transport faults. It is not electrical,
signal-integrity, DLLP/TLP bit-level, or cycle-accurate hardware emulation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


@dataclass
class VirtualPCIeBAR:
    index: int
    size_bytes: int
    memory: dict[int, int] = field(default_factory=dict)
    reads: int = 0
    writes: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.index <= 5:
            raise ValueError("VPCIE_BAR_INDEX_INVALID")
        if not _is_power_of_two(self.size_bytes) or self.size_bytes < 16:
            raise ValueError("VPCIE_BAR_SIZE_INVALID")

    def read(self, offset: int, width: int) -> int:
        self._validate_access(offset, width)
        self.reads += 1
        return sum(self.memory.get(offset + i, 0) << (8 * i) for i in range(width))

    def write(self, offset: int, value: int, width: int) -> None:
        self._validate_access(offset, width)
        if value < 0 or value >= (1 << (8 * width)):
            raise ValueError("VPCIE_MMIO_VALUE_OUT_OF_RANGE")
        for i in range(width):
            byte = (value >> (8 * i)) & 0xFF
            if byte:
                self.memory[offset + i] = byte
            else:
                self.memory.pop(offset + i, None)
        self.writes += 1

    def _validate_access(self, offset: int, width: int) -> None:
        if width not in {1, 2, 4, 8} or offset < 0 or offset % width:
            raise ValueError("VPCIE_MMIO_ALIGNMENT_INVALID")
        if offset + width > self.size_bytes:
            raise ValueError("VPCIE_MMIO_OUT_OF_BAR_RANGE")


@dataclass
class VirtualPCIeEndpoint:
    name: str
    bus: int
    device: int
    function: int = 0
    vendor_id: int = 0xB12A
    device_id: int = 0x0001
    class_code: int = 0xFF0000
    bars: dict[int, VirtualPCIeBAR] = field(default_factory=dict)
    command: int = 0x0000
    status: int = 0x0010
    config_writes: int = 0

    @property
    def bdf(self) -> str:
        return f"{self.bus:02x}:{self.device:02x}.{self.function}"

    def __post_init__(self) -> None:
        if not self.name or not 0 <= self.bus <= 255 or not 0 <= self.device <= 31 or not 0 <= self.function <= 7:
            raise ValueError("VPCIE_BDF_INVALID")
        if not 0 <= self.vendor_id <= 0xFFFF or not 0 <= self.device_id <= 0xFFFF:
            raise ValueError("VPCIE_ID_INVALID")
        if not 0 <= self.class_code <= 0xFFFFFF:
            raise ValueError("VPCIE_CLASS_CODE_INVALID")
        if any(index != bar.index for index, bar in self.bars.items()):
            raise ValueError("VPCIE_BAR_KEY_MISMATCH")

    def config_read(self, offset: int, width: int = 4) -> int:
        if width not in {1, 2, 4} or offset < 0 or offset % width or offset + width > 256:
            raise ValueError("VPCIE_CONFIG_ACCESS_INVALID")
        # Standard PCI header fields used by this model; other bytes read as zero.
        config = bytearray(256)
        config[0:2] = self.vendor_id.to_bytes(2, "little")
        config[2:4] = self.device_id.to_bytes(2, "little")
        config[4:6] = self.command.to_bytes(2, "little")
        config[6:8] = self.status.to_bytes(2, "little")
        config[9:12] = self.class_code.to_bytes(3, "little")
        config[0x0E] = 0x00  # endpoint header type
        for index, bar in self.bars.items():
            bar_offset = 0x10 + index * 4
            # Synthetic, stable MMIO address per endpoint/BAR. Not a host mapping.
            address = 0x80000000 + self.bus * 0x1000000 + self.device * 0x10000 + index * 0x1000
            config[bar_offset:bar_offset + 4] = (address & 0xFFFFFFF0).to_bytes(4, "little")
        return int.from_bytes(config[offset:offset + width], "little")

    def config_write(self, offset: int, value: int, width: int = 4) -> None:
        if width not in {1, 2, 4} or offset < 0 or offset % width or offset + width > 256:
            raise ValueError("VPCIE_CONFIG_ACCESS_INVALID")
        if value < 0 or value >= (1 << (8 * width)):
            raise ValueError("VPCIE_CONFIG_VALUE_INVALID")
        # Keep ID, class, header, and BAR registers read-only in this baseline.
        if offset >= 0x10 or offset < 4 or (offset < 0x10 and offset + width > 4):
            raise PermissionError("VPCIE_CONFIG_REGISTER_READ_ONLY")
        raw = bytearray(self.command.to_bytes(2, "little") + self.status.to_bytes(2, "little"))
        start = offset - 4
        raw[start:start + width] = value.to_bytes(width, "little")
        self.command = int.from_bytes(raw[0:2], "little")
        self.status = int.from_bytes(raw[2:4], "little")
        self.config_writes += 1


class VirtualPCIeFabric:
    """Functional PCIe endpoint/config/MMIO model with transaction traces and fault injection."""

    def __init__(self, generation: int = 4, lane_count: int = 24, trace_limit: int = 2048):
        if generation not in {1, 2, 3, 4, 5, 6, 7} or lane_count <= 0 or trace_limit <= 0:
            raise ValueError("VPCIE_FABRIC_CONFIGURATION_INVALID")
        self.generation = generation
        self.lane_count = lane_count
        self.trace_limit = trace_limit
        self.endpoints: dict[str, VirtualPCIeEndpoint] = {}
        self.transactions: list[dict[str, Any]] = []
        self.next_fault: str | None = None
        self.sequence = 0
        self.stats = {"config_reads": 0, "config_writes": 0, "mmio_reads": 0, "mmio_writes": 0,
                      "completions": 0, "timeouts": 0, "dropped": 0, "bytes_read": 0, "bytes_written": 0}

    def attach_endpoint(self, name: str, *, vendor_id: int = 0xB12A, device_id: int = 1,
                        class_code: int = 0xFF0000, bar_sizes: dict[int, int] | None = None) -> dict:
        if name in self.endpoints:
            raise ValueError(f"VPCIE_ENDPOINT_EXISTS:{name}")
        used = {(endpoint.bus, endpoint.device, endpoint.function) for endpoint in self.endpoints.values()}
        slot = next((i for i in range(1, 32) if (0, i, 0) not in used), None)
        if slot is None:
            raise RuntimeError("VPCIE_BUS_ZERO_SLOTS_EXHAUSTED")
        bars = {index: VirtualPCIeBAR(index, size) for index, size in (bar_sizes or {0: 4096}).items()}
        endpoint = VirtualPCIeEndpoint(name=name, bus=0, device=slot, vendor_id=vendor_id,
                                       device_id=device_id, class_code=class_code, bars=bars)
        self.endpoints[name] = endpoint
        return {"ok": True, "name": name, "bdf": endpoint.bdf, "vendor_id": vendor_id,
                "device_id": device_id, "bar_count": len(bars), "host_mmio_mapped": False}

    def detach_endpoint(self, name: str) -> dict:
        endpoint = self.endpoints.pop(name, None)
        if endpoint is None:
            return {"ok": False, "status": "VPCIE_ENDPOINT_NOT_FOUND", "name": name}
        return {"ok": True, "status": "DETACHED", "name": name, "bdf": endpoint.bdf}

    def inject_fault(self, fault: str) -> dict:
        if fault not in {"completion_timeout", "drop_transaction", "corrupt_completion"}:
            raise ValueError("VPCIE_FAULT_UNSUPPORTED")
        self.next_fault = fault
        return {"ok": True, "fault": fault, "deterministic": True}

    def _record(self, kind: str, endpoint: VirtualPCIeEndpoint, *, offset: int = 0,
                width: int = 4, status: str = "SUCCESS", value: int | None = None) -> dict:
        fault, self.next_fault = self.next_fault, None
        self.sequence += 1
        if fault == "completion_timeout":
            self.stats["timeouts"] += 1
            status = "COMPLETION_TIMEOUT"
        elif fault == "drop_transaction":
            self.stats["dropped"] += 1
            status = "TRANSACTION_DROPPED"
        elif fault == "corrupt_completion":
            status = "COMPLETION_ERROR"
        record = {"sequence": self.sequence, "kind": kind, "bdf": endpoint.bdf,
                  "endpoint": endpoint.name, "offset": offset, "width_bytes": width,
                  "status": status, "value": value, "link_generation": self.generation,
                  "estimated_link_latency_ns": {1: 1000, 2: 800, 3: 600, 4: 500, 5: 400, 6: 300, 7: 250}[self.generation],
                  "timing_is_estimated": True, "electrical_fidelity": False}
        self.transactions.append(record)
        if len(self.transactions) > self.trace_limit:
            del self.transactions[:len(self.transactions) - self.trace_limit]
        if status == "SUCCESS":
            self.stats["completions"] += 1
        return record

    def config_read(self, name: str, offset: int, width: int = 4) -> dict:
        endpoint = self._get(name)
        record = self._record("CONFIG_READ", endpoint, offset=offset, width=width)
        if record["status"] != "SUCCESS":
            return {"ok": False, **record, "value": None}
        value = endpoint.config_read(offset, width)
        record["value"] = value
        self.stats["config_reads"] += 1
        self.stats["bytes_read"] += width
        return {"ok": True, **record}

    def config_write(self, name: str, offset: int, value: int, width: int = 4) -> dict:
        endpoint = self._get(name)
        record = self._record("CONFIG_WRITE", endpoint, offset=offset, width=width, value=value)
        if record["status"] != "SUCCESS":
            return {"ok": False, **record}
        endpoint.config_write(offset, value, width)
        self.stats["config_writes"] += 1
        self.stats["bytes_written"] += width
        return {"ok": True, **record}

    def mmio_read(self, name: str, bar_index: int, offset: int, width: int = 4) -> dict:
        endpoint = self._get(name)
        bar = self._bar(endpoint, bar_index)
        record = self._record("MEMORY_READ", endpoint, offset=offset, width=width)
        if record["status"] != "SUCCESS":
            return {"ok": False, **record, "value": None}
        value = bar.read(offset, width)
        record["value"] = value
        self.stats["mmio_reads"] += 1
        self.stats["bytes_read"] += width
        return {"ok": True, **record}

    def mmio_write(self, name: str, bar_index: int, offset: int, value: int, width: int = 4) -> dict:
        endpoint = self._get(name)
        bar = self._bar(endpoint, bar_index)
        # Failed completions must not mutate endpoint MMIO state.
        record = self._record("MEMORY_WRITE", endpoint, offset=offset, width=width, value=value)
        if record["status"] != "SUCCESS":
            return {"ok": False, **record}
        bar.write(offset, value, width)
        self.stats["mmio_writes"] += 1
        self.stats["bytes_written"] += width
        return {"ok": True, **record}

    def _get(self, name: str) -> VirtualPCIeEndpoint:
        try:
            return self.endpoints[name]
        except KeyError as exc:
            raise KeyError("VPCIE_ENDPOINT_NOT_FOUND") from exc

    @staticmethod
    def _bar(endpoint: VirtualPCIeEndpoint, index: int) -> VirtualPCIeBAR:
        try:
            return endpoint.bars[index]
        except KeyError as exc:
            raise KeyError("VPCIE_BAR_NOT_FOUND") from exc

    def enumerate_endpoints(self) -> list[dict]:
        return [{"name": endpoint.name, "bdf": endpoint.bdf, "vendor_id": endpoint.vendor_id,
                 "device_id": endpoint.device_id, "class_code": endpoint.class_code,
                 "bars": [{"index": bar.index, "size_bytes": bar.size_bytes,
                           "reads": bar.reads, "writes": bar.writes, "host_mapping": False}
                          for bar in endpoint.bars.values()]}
                for endpoint in sorted(self.endpoints.values(), key=lambda item: item.bdf)]

    def status(self) -> dict:
        return {"generation": self.generation, "lane_count": self.lane_count,
                "endpoint_count": len(self.endpoints), "endpoints": self.enumerate_endpoints(),
                "transaction_count_retained": len(self.transactions), "trace_limit": self.trace_limit,
                "stats": dict(self.stats), "next_fault": self.next_fault,
                "protocol_fidelity": "transaction_level_functional",
                "cycle_accurate": False, "electrical_fidelity": False,
                "host_hardware_used": False, "host_mmio_mapped": False}

