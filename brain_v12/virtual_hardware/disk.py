from __future__ import annotations
import hashlib
from dataclasses import dataclass, field

@dataclass
class VirtualDisk:
    """Sparse virtual block disk used by the Brain VM.

    Blocks are materialized only when written. This avoids allocating a full
    32+ GiB disk in memory and keeps the model deterministic.
    """
    size_bytes: int = 64 * 1024 * 1024 * 1024
    block_size: int = 4096
    blocks: dict[int, bytes] = field(default_factory=dict)

    def __post_init__(self):
        if self.size_bytes <= 0 or self.block_size <= 0:
            raise ValueError("INVALID_DISK_GEOMETRY")
        if self.size_bytes % self.block_size:
            raise ValueError("DISK_SIZE_MUST_ALIGN_TO_BLOCK")

    @property
    def block_count(self) -> int:
        return self.size_bytes // self.block_size

    def _check(self, offset: int, length: int = 1):
        if offset < 0 or length < 0 or offset + length > self.size_bytes:
            raise ValueError("DISK_OUT_OF_RANGE")

    def read(self, offset: int, length: int) -> bytes:
        self._check(offset, length)
        out = bytearray(length)
        pos = 0
        while pos < length:
            absolute = offset + pos
            index = absolute // self.block_size
            within = absolute % self.block_size
            take = min(self.block_size - within, length - pos)
            block = self.blocks.get(index)
            if block:
                out[pos:pos+take] = block[within:within+take]
            pos += take
        return bytes(out)

    def write(self, offset: int, data: bytes | bytearray) -> dict:
        raw = bytes(data)
        self._check(offset, len(raw))
        pos = 0
        while pos < len(raw):
            absolute = offset + pos
            index = absolute // self.block_size
            within = absolute % self.block_size
            take = min(self.block_size - within, len(raw) - pos)
            block = bytearray(self.blocks.get(index, b"\0" * self.block_size))
            block[within:within+take] = raw[pos:pos+take]
            self.blocks[index] = bytes(block)
            pos += take
        return {"ok": True, "offset": offset, "bytes": len(raw)}

    def sha256(self, sample_bytes: int | None = None) -> str:
        h = hashlib.sha256()
        if sample_bytes is None:
            for i in range(self.block_count):
                h.update(self.blocks.get(i, b"\0" * self.block_size))
        else:
            h.update(self.read(0, min(sample_bytes, self.size_bytes)))
        return h.hexdigest()

    def snapshot(self) -> dict:
        return {
            "size_bytes": self.size_bytes,
            "block_size": self.block_size,
            "materialized_blocks": len(self.blocks),
            "sha256_sample": self.sha256(min(self.size_bytes, 1024 * 1024)),
        }
