from __future__ import annotations

class StateStore:
    """Small deterministic in-memory state contract for the first foundation gate."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        if not key:
            raise ValueError("state key is required")
        self._values[key] = value

    def get(self, key: str, default: object = None) -> object:
        return self._values.get(key, default)

    def snapshot(self) -> dict[str, object]:
        return dict(self._values)

    def restore(self, snapshot: dict[str, object]) -> None:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dict")
        self._values = dict(snapshot)

    def is_ready(self) -> bool:
        return isinstance(self._values, dict)
