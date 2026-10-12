from __future__ import annotations

from copy import deepcopy


class StateStore:
    """Small deterministic in-memory state contract with defensive snapshots."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        if not key:
            raise ValueError("state key is required")
        self._values[key] = deepcopy(value)

    def get(self, key: str, default: object = None) -> object:
        return deepcopy(self._values.get(key, default))

    def snapshot(self) -> dict[str, object]:
        return deepcopy(self._values)

    def restore(self, snapshot: dict[str, object]) -> None:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dict")
        self._values = deepcopy(snapshot)

    def is_ready(self) -> bool:
        return isinstance(self._values, dict)
