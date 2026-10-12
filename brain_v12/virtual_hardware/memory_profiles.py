"""Source-backed DRAM reference profiles and explicitly approximate cache/timing models."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import OrderedDict
from typing import Any


MICRON_DDR4 = "https://www.micron.com/products/memory/dram-components/ddr4-sdram/part-catalog/part-detail/mt40a2g8jc-062e-e"
MICRON_DDR5 = "https://www.micron.com/products/memory/dram-components/ddr5-sdram/part-catalog/part-detail/mt60b1g16hc-56b-g"
MICRON_LPDDR5X = "https://www.micron.com/products/memory/lpddr-components/lpddr5x/part-catalog/part-detail/mt62f768m64d4cz-023-aut-c"


@dataclass(frozen=True)
class MemoryProfile:
    profile_id: str
    vendor: str
    model: str
    technology: str
    component_density_bits: int
    transfer_rate_mt_s: int
    component_width_bits: int
    cas_latency_cycles: int | None
    voltage_v: float
    source_url: str
    source_note: str
    t_rcd_cycles: int | None = None
    t_rp_cycles: int | None = None
    t_ras_cycles: int | None = None
    bank_count: int | None = None
    fidelity: str = "timing_model"

    def describe(self, channels: int = 1, channel_width_bits: int = 64,
                 configured_cas_latency_cycles: int | None = None) -> dict:
        cas = configured_cas_latency_cycles if configured_cas_latency_cycles is not None else self.cas_latency_cycles
        cas_ns = (cas * 2000 / self.transfer_rate_mt_s) if cas is not None else None
        peak_bandwidth = self.transfer_rate_mt_s * 1_000_000 * channel_width_bits * channels // 8
        return {
            "profile_id": self.profile_id, "vendor": self.vendor, "model": self.model,
            "technology": self.technology, "component_density_bits": self.component_density_bits,
            "transfer_rate_mt_s": self.transfer_rate_mt_s, "component_width_bits": self.component_width_bits,
            "cas_latency_cycles": cas, "cas_latency_ns_estimate": cas_ns, "voltage_v": self.voltage_v,
            "cas_latency_configuration_source": "vendor_spec" if self.cas_latency_cycles is not None else ("simulator_assumption" if configured_cas_latency_cycles is not None else "not_configured"),
            "t_rcd_cycles": self.t_rcd_cycles, "t_rp_cycles": self.t_rp_cycles,
            "t_ras_cycles": self.t_ras_cycles, "bank_count": self.bank_count,
            "channels": channels, "channel_width_bits": channel_width_bits,
            "channel_width_is_platform_assumption": True,
            "peak_theoretical_bandwidth_bytes_per_second": peak_bandwidth,
            "fidelity": self.fidelity, "source_url": self.source_url, "source_note": self.source_note,
            "unsupported_features": ["full DRAM command protocol", "PHY/electrical training",
                "complete timing-bin validation", "ECC signaling", "vendor-specific refresh behavior",
                "measured physical latency/bandwidth"],
            "physical_measurement": False,
        }


MEMORY_PROFILES: dict[str, MemoryProfile] = {
    "micron-ddr4-3200-x8": MemoryProfile(
        "micron-ddr4-3200-x8", "Micron", "MT40A2G8JC-062E:E reference component",
        "DDR4", 16_000_000_000, 3200, 8, 22, 1.2, MICRON_DDR4,
        "Micron lists 16Gb density, x8 width, 3200 MT/s and CL22. Other timings are not inferred.",
    ),
    "micron-ddr5-5600-x16": MemoryProfile(
        "micron-ddr5-5600-x16", "Micron", "MT60B1G16HC-56B:G reference component",
        "DDR5", 16_000_000_000, 5600, 16, 46, 1.1, MICRON_DDR5,
        "Micron lists 16Gb density, x16 width, 5600 MT/s and CL46. Other timings are not inferred.",
    ),
    "micron-lpddr5x-8533-x64": MemoryProfile(
        "micron-lpddr5x-8533-x64", "Micron", "MT62F768M64D4CZ-023-AUT:C reference component",
        "LPDDR5X", 48_000_000_000, 8533, 64, None, 0.5, MICRON_LPDDR5X,
        "Micron lists 48Gb density, x64 width and 8533 MT/s; CAS latency is programmable.",
    ),
}


def get_memory_profile(profile_id: str) -> MemoryProfile:
    try:
        return MEMORY_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_MEMORY_PROFILE:{profile_id}") from exc


def list_memory_profiles() -> list[dict]:
    return [MEMORY_PROFILES[key].describe() for key in sorted(MEMORY_PROFILES)]


@dataclass(frozen=True)
class CacheLevelProfile:
    name: str
    size_bytes: int
    line_size_bytes: int = 64
    associativity: int = 8
    hit_latency_cycles: int = 1

    def __post_init__(self):
        if self.size_bytes <= 0 or self.line_size_bytes <= 0 or self.associativity <= 0 or self.hit_latency_cycles <= 0:
            raise ValueError("CACHE_PROFILE_PARAMETERS_INVALID")
        if self.size_bytes % (self.line_size_bytes * self.associativity):
            raise ValueError("CACHE_SIZE_MUST_BE_MULTIPLE_OF_SET_SIZE")

    @property
    def set_count(self) -> int:
        return self.size_bytes // (self.line_size_bytes * self.associativity)


@dataclass
class _CacheState:
    profile: CacheLevelProfile
    sets: dict[int, OrderedDict[int, None]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def access(self, address: int) -> bool:
        line = address // self.profile.line_size_bytes
        set_index = line % self.profile.set_count
        tag = line // self.profile.set_count
        ways = self.sets.setdefault(set_index, OrderedDict())
        hit = tag in ways
        if hit:
            self.hits += 1
            ways.move_to_end(tag)
        else:
            self.misses += 1
            ways[tag] = None
            if len(ways) > self.profile.associativity:
                ways.popitem(last=False)
        return hit


@dataclass
class CacheHierarchy:
    """Deterministic set-associative L1/L2/L3 tag model; no data cache or coherence protocol."""
    levels: tuple[CacheLevelProfile, ...] = (
        CacheLevelProfile("L1", 32 * 1024, 64, 8, 1),
        CacheLevelProfile("L2", 256 * 1024, 64, 8, 4),
        CacheLevelProfile("L3", 8 * 1024 * 1024, 64, 16, 12),
    )
    _states: list[_CacheState] = field(init=False)

    def __post_init__(self):
        names = [level.name for level in self.levels]
        if names != ["L1", "L2", "L3"]:
            raise ValueError("CACHE_HIERARCHY_REQUIRES_ORDERED_L1_L2_L3")
        self._states = [_CacheState(level) for level in self.levels]

    def access(self, address: int) -> dict:
        if address < 0:
            raise ValueError("CACHE_ADDRESS_NEGATIVE")
        accumulated_cycles = 0
        hit_level = "DRAM"
        for state in self._states:
            accumulated_cycles += state.profile.hit_latency_cycles
            if state.access(address):
                hit_level = state.profile.name
                break
        return {"address": address, "hit_level": hit_level,
                "estimated_hit_latency_cycles": accumulated_cycles,
                "timing_is_approximate": True, "cycle_accurate": False}

    def snapshot(self) -> dict:
        return {"fidelity": "functional_tag_plus_approximate_timing",
                "levels": [{"name": s.profile.name, "size_bytes": s.profile.size_bytes,
                            "line_size_bytes": s.profile.line_size_bytes,
                            "associativity": s.profile.associativity,
                            "hit_latency_cycles": s.profile.hit_latency_cycles,
                            "hits": s.hits, "misses": s.misses} for s in self._states],
                "data_values_cached": False, "coherence_modeled": False,
                "cycle_accurate": False, "host_cache_data_bytes_allocated": 0,
                "host_tag_metadata_bytes_estimated": None, "host_rss_measured": False}


@dataclass
class MemoryTimingModel:
    profile: MemoryProfile
    channels: int = 1
    channel_width_bits: int = 64
    configured_cas_latency_cycles: int | None = None
    bank_count: int = 8
    max_outstanding: int = 16
    outstanding: dict[str, dict[str, Any]] = field(default_factory=dict)
    accesses: int = 0
    bytes_transferred: int = 0
    contention_events: int = 0

    def __post_init__(self):
        if self.channels < 1 or self.channel_width_bits < 8 or self.bank_count < 1 or self.max_outstanding < 1:
            raise ValueError("MEMORY_TIMING_PARAMETERS_INVALID")
        if self.configured_cas_latency_cycles is None:
            self.configured_cas_latency_cycles = self.profile.cas_latency_cycles or 32
        if self.configured_cas_latency_cycles < 1:
            raise ValueError("MEMORY_CAS_LATENCY_INVALID")

    def begin_access(self, address: int, size_bytes: int, operation: str = "read") -> dict:
        if address < 0 or size_bytes < 0 or operation not in {"read", "write"}:
            raise ValueError("MEMORY_ACCESS_ARGUMENT_INVALID")
        if len(self.outstanding) >= self.max_outstanding:
            raise RuntimeError("MEMORY_REQUEST_QUEUE_FULL")
        bank = (address // 64) % self.bank_count
        conflict = any(request["bank"] == bank for request in self.outstanding.values())
        if conflict:
            self.contention_events += 1
        report = self.profile.describe(self.channels, self.channel_width_bits, self.configured_cas_latency_cycles)
        base_ns = report["cas_latency_ns_estimate"]
        bandwidth = max(1, report["peak_theoretical_bandwidth_bytes_per_second"])
        transfer_ns = size_bytes / bandwidth * 1_000_000_000
        penalty_ns = len(self.outstanding) * base_ns + (base_ns if conflict else 0)
        token = f"mem-{self.accesses + len(self.outstanding) + 1}-{address}-{size_bytes}"
        self.outstanding[token] = {"bank": bank, "address": address, "size_bytes": size_bytes, "operation": operation}
        return {"ok": True, "token": token, "bank": bank,
                "estimated_latency_ns": base_ns + transfer_ns + penalty_ns,
                "estimated_peak_bandwidth_bytes_per_second": bandwidth,
                "queue_depth": len(self.outstanding), "bank_conflict": conflict,
                "timing_is_approximate": True, "physical_measurement": False}

    def complete_access(self, token: str) -> dict:
        request = self.outstanding.pop(token, None)
        if request is None:
            raise KeyError("MEMORY_UNKNOWN_REQUEST")
        self.accesses += 1
        self.bytes_transferred += request["size_bytes"]
        return {"ok": True, **request, "queue_depth": len(self.outstanding)}

    def snapshot(self) -> dict:
        report = self.profile.describe(self.channels, self.channel_width_bits, self.configured_cas_latency_cycles)
        return {**report, "accesses": self.accesses, "bytes_transferred": self.bytes_transferred,
                "outstanding_requests": len(self.outstanding), "contention_events": self.contention_events,
                "fidelity": "analytical_timing_estimate", "physical_measurement": False,
                "host_ram_allocated_for_simulated_capacity_bytes": 0}
