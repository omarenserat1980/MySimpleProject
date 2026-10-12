from __future__ import annotations

from .memory_profiles import CacheHierarchy, MemoryTimingModel, get_memory_profile


class _SparseCellArray:
    """List-like compatibility view over sparse RAM cells; does not allocate size entries."""
    def __init__(self, owner):
        self._owner = owner

    def __len__(self):
        return self._owner.size

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self._owner.size)
            return [self._owner._cells.get(i, 0) for i in range(start, stop, step)]
        index = int(index)
        if index < 0:
            index += self._owner.size
        self._owner._check(index)
        return self._owner._cells.get(index, 0)

    def __setitem__(self, index, value):
        index = int(index)
        if index < 0:
            index += self._owner.size
        self._owner.write(index, int(value))

    def __iter__(self):
        return (self._owner._cells.get(i, 0) for i in range(self._owner.size))


class VirtualRAM:
    """Sparse addressable-cell RAM with optional DRAM timing and cache tag models.

    Logical capacity is the number of addressable cells. It is not a promise to allocate an
    equivalent number of bytes in the host process. Cell values remain integers for backward
    compatibility and are not constrained to an 8-bit physical byte.
    """
    def __init__(self, size: int = 65536, profile_id: str | None = None,
                 channels: int = 1, channel_width_bits: int = 64,
                 configured_cas_latency_cycles: int | None = None,
                 cache_enabled: bool = False, cache_levels=None):
        if size <= 0:
            raise ValueError("RAM_SIZE_MUST_BE_POSITIVE")
        self.size = int(size)
        self.profile_id = profile_id
        self.profile = get_memory_profile(profile_id) if profile_id else None
        self._cells: dict[int, int] = {}
        self._data = _SparseCellArray(self)
        self.timing_model = (MemoryTimingModel(self.profile, channels, channel_width_bits,
                                               configured_cas_latency_cycles)
                             if self.profile else None)
        self.cache_hierarchy = CacheHierarchy(tuple(cache_levels)) if cache_levels else (CacheHierarchy() if cache_enabled else None)
        self.last_access_report = None

    def _check(self, address: int):
        if not 0 <= address < self.size:
            raise IndexError("RAM_ADDRESS_OUT_OF_RANGE")

    @property
    def used_cells(self) -> int:
        return len(self._cells)

    @property
    def host_payload_bytes_estimate(self) -> int:
        return sum(max(1, (abs(value).bit_length() + 7) // 8) for value in self._cells.values())

    def _record_access(self, address: int, operation: str):
        reports = {}
        if self.cache_hierarchy:
            reports["cache"] = self.cache_hierarchy.access(address)
        if self.timing_model:
            request = self.timing_model.begin_access(address, 1, operation)
            self.timing_model.complete_access(request["token"])
            reports["dram"] = request
        if reports:
            self.last_access_report = reports

    def read(self, address: int) -> int:
        self._check(address)
        self._record_access(address, "read")
        return self._cells.get(address, 0)

    def write(self, address: int, value: int) -> None:
        self._check(address)
        self._record_access(address, "write")
        value = int(value)
        if value == 0:
            self._cells.pop(address, None)
        else:
            self._cells[address] = value

    def snapshot(self) -> dict:
        return {"size": self.size, "capacity_unit": "addressable_cells",
                "nonzero": {str(i): v for i, v in sorted(self._cells.items())},
                "profile_id": self.profile_id,
                "host_payload_bytes_estimate": self.host_payload_bytes_estimate}

    def restore(self, snapshot: dict) -> None:
        if int(snapshot.get("size", self.size)) != self.size:
            raise ValueError("RAM_SIZE_MISMATCH")
        restored = {}
        for key, value in (snapshot.get("nonzero") or {}).items():
            address = int(key)
            self._check(address)
            value = int(value)
            if value:
                restored[address] = value
        self._cells = restored

    def status(self) -> dict:
        return {
            "logical_capacity_cells": self.size,
            "used_cells": self.used_cells,
            "free_cells": self.size - self.used_cells,
            "capacity_unit": "addressable_cells",
            "profile_id": self.profile_id,
            "host_payload_bytes_estimate": self.host_payload_bytes_estimate,
            "host_rss_measured": False,
            "host_buffer_allocated_for_full_capacity": False,
            "dram_timing": self.timing_model.snapshot() if self.timing_model else None,
            "cache_hierarchy": self.cache_hierarchy.snapshot() if self.cache_hierarchy else None,
        }
