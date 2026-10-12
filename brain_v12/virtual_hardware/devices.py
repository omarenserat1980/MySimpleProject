from __future__ import annotations
import hashlib
import posixpath
from uuid import uuid4

from .storage_profiles import get_storage_profile


class VirtualStorage:
    """In-memory virtual block device with modeled SSD timing and explicit durability.

    Logical capacity is metadata only; no disk image or host block device is allocated/opened.
    Modeled latency and throughput are estimates derived from profile limits, never measurements.
    """
    def __init__(self, capacity: int | None = None, profile_id: str | None = None,
                 queue_depth: int | None = None, cache_mode: str | None = None):
        self.profile = get_storage_profile(profile_id) if profile_id else None
        default_capacity = self.profile.capacity_bytes if self.profile else 1024 * 1024
        self.capacity = int(default_capacity if capacity is None else capacity)
        if self.capacity <= 0:
            raise ValueError("VSTORAGE_CAPACITY_MUST_BE_POSITIVE")
        self.logical_capacity_bytes = self.capacity
        self.profile_id = profile_id
        self.block_size_bytes = self.profile.block_size_bytes if self.profile else 4096
        self.max_queue_depth = self.profile.max_queue_depth if self.profile else 1
        self.queue_depth = int(queue_depth if queue_depth is not None else 1)
        if not 1 <= self.queue_depth <= self.max_queue_depth:
            raise ValueError("VSTORAGE_QUEUE_DEPTH_OUT_OF_RANGE")
        self.cache_mode = cache_mode or ("write_back" if self.profile else "write_through")
        if self.cache_mode not in {"write_back", "write_through"}:
            raise ValueError("VSTORAGE_CACHE_MODE_INVALID")
        self.cache_capacity_bytes = self.profile.cache_bytes if self.profile else 0
        self.files: dict[str, bytes] = {}
        self.durable_files: dict[str, bytes] = {}
        self.inflight: dict[str, dict] = {}
        self._next_fault: str | None = None
        self.stats = {"read_ops": 0, "write_ops": 0, "flush_ops": 0, "trim_ops": 0,
                      "bytes_read": 0, "bytes_written": 0, "bytes_trimmed": 0,
                      "timeouts": 0, "resets": 0, "power_losses": 0}
        self.dirty_bytes = 0
        self._modeled_latency_total_us = 0.0

    @staticmethod
    def normalize_path(path: str) -> str:
        if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
            raise ValueError("VSTORAGE_INVALID_PATH")
        parts = path.split("/")
        if any(part == ".." for part in parts):
            raise ValueError("VSTORAGE_PATH_TRAVERSAL")
        normalized = posixpath.normpath("/" + path.lstrip("/"))
        if normalized == "/." or normalized == "/":
            raise ValueError("VSTORAGE_INVALID_PATH")
        return normalized

    def _consume_fault(self, operation: str) -> None:
        fault = self._next_fault
        if fault is None:
            return
        self._next_fault = None
        if fault == "timeout":
            self.stats["timeouts"] += 1
            raise TimeoutError("VSTORAGE_INJECTED_TIMEOUT")
        if fault == "device_reset":
            self.stats["resets"] += 1
            self.inflight.clear()
            raise RuntimeError("VSTORAGE_DEVICE_RESET")
        if fault == "power_loss":
            self.stats["power_losses"] += 1
            self.restart()
            raise RuntimeError("VSTORAGE_POWER_LOSS")
        if fault == "queue_full":
            raise RuntimeError("VSTORAGE_QUEUE_FULL")

    def inject_fault(self, fault: str) -> dict:
        if fault not in {"timeout", "device_reset", "power_loss", "queue_full"}:
            raise ValueError(f"VSTORAGE_UNKNOWN_FAULT:{fault}")
        self._next_fault = fault
        return {"ok": True, "fault": fault, "deterministic": True}

    def _limits(self, operation: str) -> tuple[int, int]:
        if not self.profile:
            return 100 * 1024 * 1024, 1000
        if operation == "read":
            qd1, qd32 = self.profile.random_read_iops_qd1, self.profile.random_read_iops_qd32
        else:
            qd1, qd32 = self.profile.random_write_iops_qd1, self.profile.random_write_iops_qd32
        # The datasheets publish QD1 and QD32 points, not a full curve. Intermediate
        # queue depths use a labeled linear interpolation rather than invented measurements.
        modeled_iops = int(qd1 + (min(self.queue_depth, 32) - 1) * (qd32 - qd1) / 31)
        throughput = (self.profile.sequential_read_bytes_per_second if operation == "read"
                      else self.profile.sequential_write_bytes_per_second)
        return throughput, max(1, modeled_iops)

    def estimate_latency_us(self, operation: str, size_bytes: int, outstanding: int = 1) -> float:
        if operation not in {"read", "write"} or size_bytes < 0:
            raise ValueError("VSTORAGE_LATENCY_ARGUMENT_INVALID")
        throughput, iops = self._limits(operation)
        transfer_us = (size_bytes / max(1, throughput)) * 1_000_000
        service_us = 1_000_000 / max(1, iops)
        queue_penalty_us = max(0, outstanding - 1) * service_us / max(1, self.max_queue_depth)
        return max(transfer_us, service_us) + queue_penalty_us

    def begin_io(self, operation: str, size_bytes: int) -> dict:
        if operation not in {"read", "write", "flush", "trim"} or size_bytes < 0:
            raise ValueError("VSTORAGE_IO_ARGUMENT_INVALID")
        self._consume_fault(operation)
        if len(self.inflight) >= self.queue_depth:
            raise RuntimeError("VSTORAGE_QUEUE_FULL")
        token = uuid4().hex
        latency = self.estimate_latency_us(operation, size_bytes, len(self.inflight) + 1) if operation in {"read", "write"} else 0.0
        self.inflight[token] = {"operation": operation, "size_bytes": int(size_bytes), "estimated_latency_us": latency}
        return {"ok": True, "token": token, "queue_depth": len(self.inflight),
                "estimated_latency_us": latency, "timing_is_estimated": True}

    def complete_io(self, token: str) -> dict:
        request = self.inflight.pop(token, None)
        if request is None:
            raise KeyError("VSTORAGE_UNKNOWN_IO_TOKEN")
        op = request["operation"]
        if op in {"read", "write"}:
            self._modeled_latency_total_us += request["estimated_latency_us"]
            self.stats[f"{op}_ops"] += 1
            byte_counter = "bytes_read" if op == "read" else "bytes_written"
            self.stats[byte_counter] += request["size_bytes"]
        return {"ok": True, **request, "queue_depth": len(self.inflight),
                "timing_is_estimated": True, "physical_measurement": False}

    def _record_io(self, operation: str, size_bytes: int) -> dict:
        request = self.begin_io(operation, size_bytes)
        return self.complete_io(request["token"])

    def write(self, path: str, data: bytes):
        path = self.normalize_path(path)
        payload = bytes(data)
        self._consume_fault("write")
        used = sum(len(value) for value in self.files.values())
        old = len(self.files.get(path, b""))
        if used - old + len(payload) > self.capacity:
            raise RuntimeError("VSTORAGE_FULL")
        previous_dirty = old if path not in self.durable_files or self.files.get(path) != self.durable_files.get(path) else 0
        io = self._record_io("write", len(payload))
        self.files[path] = payload
        self.dirty_bytes = max(0, self.dirty_bytes - previous_dirty) + len(payload)
        if self.cache_mode == "write_through":
            self.durable_files[path] = payload
            self.dirty_bytes = max(0, self.dirty_bytes - len(payload))
        elif self.cache_capacity_bytes and self.dirty_bytes > self.cache_capacity_bytes:
            self.flush()
        return {**io, "path": path, "size": len(payload), "durable": self.cache_mode == "write_through"}

    def read(self, path: str) -> bytes:
        path = self.normalize_path(path)
        self._consume_fault("read")
        if path not in self.files:
            raise FileNotFoundError(path)
        self._record_io("read", len(self.files[path]))
        return self.files[path]

    def flush(self) -> dict:
        self._consume_fault("flush")
        self.durable_files = dict(self.files)
        self.dirty_bytes = 0
        self.stats["flush_ops"] += 1
        return {"ok": True, "durable": True, "files_flushed": len(self.files),
                "dirty_bytes": 0, "host_disk_write": False}

    def restart(self) -> dict:
        """Recover after simulated process/device restart; unflushed writes are discarded."""
        lost = sum(len(v) for k, v in self.files.items() if self.durable_files.get(k) != v)
        self.files = dict(self.durable_files)
        self.inflight.clear()
        self.dirty_bytes = 0
        return {"ok": True, "recovered": True, "unflushed_bytes_lost": lost,
                "host_disk_allocation_bytes": 0}

    def trim(self, path: str) -> dict:
        path = self.normalize_path(path)
        self._consume_fault("trim")
        old = self.files.pop(path, None)
        self.durable_files.pop(path, None)
        released = len(old) if old is not None else 0
        self.stats["trim_ops"] += 1
        self.stats["bytes_trimmed"] += released
        self.dirty_bytes = sum(len(v) for k, v in self.files.items() if self.durable_files.get(k) != v)
        return {"ok": True, "path": path, "bytes_released_logically": released,
                "trim_supported": bool(self.profile and self.profile.trim_supported),
                "physical_nand_erasure_claim": False}

    def smart_telemetry(self) -> dict:
        endurance_bytes = self.profile.endurance_tbw * 1_000_000_000_000 if self.profile else None
        written = self.stats["bytes_written"]
        return {
            "profile_id": self.profile_id,
            "logical_capacity_bytes": self.logical_capacity_bytes,
            "in_process_payload_bytes": sum(map(len, self.files.values())) + sum(map(len, self.durable_files.values())),
            "host_disk_allocation_bytes": 0,
            "read_ops": self.stats["read_ops"], "write_ops": self.stats["write_ops"],
            "bytes_read": self.stats["bytes_read"], "bytes_written": written,
            "flush_ops": self.stats["flush_ops"], "trim_ops": self.stats["trim_ops"],
            "queue_depth_configured": self.queue_depth, "queue_depth_current": len(self.inflight),
            "estimated_average_latency_us": self._modeled_latency_total_us / max(1, self.stats["read_ops"] + self.stats["write_ops"]),
            "endurance_tbw_reference": self.profile.endurance_tbw if self.profile else None,
            "estimated_wear_percent": min(100.0, written / endurance_bytes * 100) if endurance_bytes else None,
            "temperature_c": None,
            "timing_and_wear_are_estimates": True,
            "smart_protocol_implemented": False,
        }

    def manifest(self):
        return {p: {"size": len(v), "sha256": hashlib.sha256(v).hexdigest()} for p, v in sorted(self.files.items())}

class VirtualNIC:
    def __init__(self,mac:str="02:42:42:52:00:01"):
        self.mac=mac; self.rx=[]; self.tx=[]
    def send(self,payload:bytes):
        packet=bytes(payload); self.tx.append(packet); return {"ok":True,"bytes":len(packet)}
    def inject(self,payload:bytes):
        packet=bytes(payload); self.rx.append(packet); return {"ok":True,"bytes":len(packet)}
    def receive(self):
        return self.rx.pop(0) if self.rx else None

class VirtualGPU:
    def __init__(self,width:int=320,height:int=200):
        self.width=width; self.height=height; self.framebuffer=[0]*(width*height)
    def clear(self,value:int=0):
        self.framebuffer=[int(value)]*(self.width*self.height)
    def pixel(self,x:int,y:int,value:int):
        if not (0<=x<self.width and 0<=y<self.height): raise IndexError("GPU_COORDINATES_OUT_OF_RANGE")
        self.framebuffer[y*self.width+x]=int(value)
