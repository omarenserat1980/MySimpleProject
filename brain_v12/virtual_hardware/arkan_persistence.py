"""Durable checkpoint storage for the canonical software-defined Arkan.

This stores simulator state only. It is not a native VM disk or Windows guest image.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .arkan_provisioner import ARKAN_ID, default_registry_path

CHECKPOINT_SCHEMA_VERSION = 1
CHECKPOINT_ENV = "BRAIN_ARKAN_CHECKPOINT_PATH"


def default_checkpoint_path() -> Path:
    configured = os.environ.get(CHECKPOINT_ENV)
    if configured:
        return Path(configured).expanduser()
    return default_registry_path().with_suffix(".checkpoint.json")


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _atomic_private_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def save_arkan_checkpoint(checkpoint: dict[str, Any], path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Validate and atomically persist a checksummed checkpoint for canonical Arkan."""
    if not isinstance(checkpoint, dict) or checkpoint.get("machine_id") != ARKAN_ID:
        raise ValueError("ARKAN_CHECKPOINT_MACHINE_ID_INVALID")
    embedded_checksum = checkpoint.get("checksum_sha256")
    payload = dict(checkpoint)
    payload.pop("checksum_sha256", None)
    expected = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    if not embedded_checksum or embedded_checksum != expected:
        raise ValueError("ARKAN_CHECKPOINT_CHECKSUM_INVALID")
    target = Path(path).expanduser() if path is not None else default_checkpoint_path()
    envelope: dict[str, Any] = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "device_id": ARKAN_ID,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": checkpoint,
    }
    envelope["envelope_sha256"] = hashlib.sha256(_canonical_bytes(envelope)).hexdigest()
    _atomic_private_json(target, envelope)
    return {"ok": True, "device_id": ARKAN_ID, "checkpoint_path": str(target),
            "checkpoint_sha256": embedded_checksum, "saved_at": envelope["saved_at"]}


def load_arkan_checkpoint(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load and verify durable simulator state. Never synthesizes a missing checkpoint."""
    target = Path(path).expanduser() if path is not None else default_checkpoint_path()
    try:
        envelope = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError("ARKAN_CHECKPOINT_NOT_FOUND") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("ARKAN_CHECKPOINT_UNREADABLE") from exc
    if not isinstance(envelope, dict) or envelope.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("ARKAN_CHECKPOINT_SCHEMA_INVALID")
    if envelope.get("device_id") != ARKAN_ID:
        raise ValueError("ARKAN_CHECKPOINT_MACHINE_ID_INVALID")
    checksum = envelope.get("envelope_sha256")
    payload = dict(envelope)
    payload.pop("envelope_sha256", None)
    if not checksum or checksum != hashlib.sha256(_canonical_bytes(payload)).hexdigest():
        raise ValueError("ARKAN_CHECKPOINT_ENVELOPE_CHECKSUM_INVALID")
    checkpoint = envelope.get("checkpoint")
    if not isinstance(checkpoint, dict) or checkpoint.get("machine_id") != ARKAN_ID:
        raise ValueError("ARKAN_CHECKPOINT_MACHINE_ID_INVALID")
    embedded = dict(checkpoint)
    embedded_checksum = embedded.pop("checksum_sha256", None)
    if not embedded_checksum or embedded_checksum != hashlib.sha256(_canonical_bytes(embedded)).hexdigest():
        raise ValueError("ARKAN_CHECKPOINT_CHECKSUM_INVALID")
    return {"device_id": ARKAN_ID, "checkpoint": checkpoint, "saved_at": envelope.get("saved_at"),
            "checkpoint_path": str(target)}
