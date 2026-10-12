"""Least-privilege capability registry for Brain Habitat.

This module never grants Android/root privileges. It only records capabilities
that the connected executor has explicitly declared and enforces an allowlist.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    risk: str = "low"
    requires_permission: bool = False


DEFAULT_CAPABILITIES = (
    Capability("files.read", "Read files inside the Brain workspace."),
    Capability("files.write", "Write files inside the Brain workspace.", "medium"),
    Capability("project.create", "Create a project skeleton inside the workspace.", "medium"),
    Capability("source.inspect", "Inspect source files inside registered roots."),
    Capability("app.open", "Launch an installed Android application.", "medium", True),
    Capability("url.open", "Open an HTTP(S) URL with the Android system handler.", "medium", True),
    Capability("network.download", "Download HTTP(S) content to the allowed Downloads area.", "medium", True),
)


class CapabilityManager:
    def __init__(self, state_file: str | Path, capabilities=DEFAULT_CAPABILITIES):
        self.state_file = Path(state_file)
        self.capabilities = {c.name: c for c in capabilities}
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.state_file.exists():
            return {"enabled": {}, "updated_at": None}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"enabled": {}, "updated_at": None}

    def _save(self, state: dict) -> None:
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_file)

    def declare(self, name: str, enabled: bool = True) -> dict:
        if name not in self.capabilities:
            raise ValueError(f"unknown capability: {name}")
        state = self._load()
        state["enabled"][name] = bool(enabled)
        state["updated_at"] = time.time()
        self._save(state)
        return self.status(name)

    def allowed(self, name: str) -> bool:
        if name not in self.capabilities:
            return False
        return bool(self._load()["enabled"].get(name, False))

    def require(self, name: str) -> None:
        if name not in self.capabilities:
            raise PermissionError(f"unknown capability: {name}")
        if not self.allowed(name):
            raise PermissionError(f"capability disabled: {name}")

    def status(self, name: str | None = None) -> dict:
        state = self._load()
        names = [name] if name else sorted(self.capabilities)
        return {
            "ok": True,
            "capabilities": [
                {
                    "name": n,
                    "enabled": bool(state["enabled"].get(n, False)),
                    "risk": self.capabilities[n].risk,
                    "requires_permission": self.capabilities[n].requires_permission,
                    "description": self.capabilities[n].description,
                }
                for n in names if n in self.capabilities
            ],
        }
