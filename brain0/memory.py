"""Durable memory layer for BRAIN-0/1 with optional atomic persistence."""
from dataclasses import dataclass, field
import hashlib
import json
import os
import tempfile


@dataclass
class Memory:
    values: dict[str, object] = field(default_factory=dict)
    version: int = 0
    path: str | None = None

    def __post_init__(self):
        if self.path:
            self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        if not isinstance(state, dict) or not isinstance(state.get("values"), dict):
            raise ValueError("MEMORY_STATE_INVALID")
        self.values = state["values"]
        self.version = int(state.get("version", 0))

    def _persist(self):
        if not self.path:
            return
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        state = {"version": self.version, "values": self.values}
        fd, tmp = tempfile.mkstemp(prefix=".memory-", dir=parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(state, fh, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def put(self, key, value):
        self.values[key] = value
        self.version += 1
        self._persist()
        return self.version

    def get(self, key, default=None):
        return self.values.get(key, default)

    def snapshot(self):
        raw = json.dumps(
            self.values, sort_keys=True, separators=(",", ":"), default=str
        ).encode()
        return {
            "version": self.version,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "values": dict(self.values),
        }
