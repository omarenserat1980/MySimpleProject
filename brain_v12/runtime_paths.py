"""Writable locations for Electronic Brain runtime state.

Persistent operational data belongs in a user-writable runtime directory, not
inside the source checkout. Explicit BRAIN_* path overrides always take priority.
"""
from __future__ import annotations

import os
from pathlib import Path


def configure_runtime_paths() -> Path:
    """Set writable defaults for runtime data and return the runtime home."""
    configured_home = os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")
    runtime_home = Path(configured_home).expanduser().resolve()
    runtime_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("BRAIN_RUNTIME_HOME", str(runtime_home))

    defaults = {
        "BRAIN_DB": runtime_home / "brain_v12.db",
        "BRAIN_SYNC_QUEUE": runtime_home / "state" / "sync_queue.jsonl",
        "BRAIN_GIT_ROOT": runtime_home / "brain_git_data",
        "BRAIN_EVIDENCE_DB": runtime_home / "brain6_artifacts" / "evidence" / "evidence.db",
        "BRAIN_MEDIA_ROOT": runtime_home / "media",
    }
    for name, default_path in defaults.items():
        os.environ.setdefault(name, str(default_path.resolve()))
    return runtime_home
