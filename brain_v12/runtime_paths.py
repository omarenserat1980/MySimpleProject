"""Writable locations for Electronic Brain runtime state.

Persistent operational data belongs outside the source checkout when possible.
Legacy state is copied only when the new destination is absent. Original files
are never deleted or overwritten by this module.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


def _copy_file_if_missing(source: Path, destination: Path) -> None:
    if destination.exists() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".migrating", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        if not destination.exists():
            # link() is exclusive: a concurrent creator is never overwritten.
            os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_sqlite_if_missing(source: Path, destination: Path) -> None:
    """Use SQLite's backup API so WAL-backed source databases are copied safely."""
    if destination.exists() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".migrating", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    source_db = None
    target_db = None
    try:
        source_uri = source.resolve().as_uri() + "?mode=ro"
        source_db = sqlite3.connect(source_uri, uri=True)
        target_db = sqlite3.connect(temporary)
        source_db.backup(target_db)
        target_db.close()
        target_db = None
        source_db.close()
        source_db = None
        if not destination.exists():
            os.link(temporary, destination)
    finally:
        if target_db is not None:
            target_db.close()
        if source_db is not None:
            source_db.close()
        temporary.unlink(missing_ok=True)


def _copy_tree_if_missing(source: Path, destination: Path) -> None:
    if destination.exists() or not source.is_dir():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(
        prefix=f".{destination.name}.", suffix=".migrating", dir=destination.parent
    ))
    shutil.rmtree(temporary)
    try:
        shutil.copytree(source, temporary)
        if not destination.exists():
            # rename is within the same parent filesystem and does not merge trees.
            os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def configure_runtime_paths(source_root: str | os.PathLike[str] | None = None) -> Path:
    """Set writable defaults and one-time copy legacy state into runtime storage.

    Explicit BRAIN_* path settings are preserved. A legacy path is copied only
    for a setting that was not explicitly provided and only when the destination
    does not exist. The original database, queue, and workflow tree remain intact.
    """
    explicit = set(os.environ)
    source = Path(source_root or Path(__file__).resolve().parent).expanduser().resolve()
    configured_home = os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")
    runtime_home = Path(configured_home).expanduser().resolve()
    runtime_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("BRAIN_RUNTIME_HOME", str(runtime_home))

    legacy = {
        "BRAIN_DB": source / "brain_v12.db",
        "BRAIN_SYNC_QUEUE": source / ".brain" / "state" / "sync_queue.jsonl",
        "BRAIN_GIT_ROOT": source / "brain_git_data",
        "BRAIN_EVIDENCE_DB": source / "brain6_artifacts" / "evidence" / "evidence.db",
        "AGENT_SANDBOX": source.parent / "agent_sandbox",
        "BRAIN_SUPERVISOR_ROOT": source.parent / "brain6_artifacts" / "supervisor",
        "BRAIN_SUCCESS_BOT_ROOT": source.parent / "brain6_artifacts" / "success_bot",
    }
    defaults = {
        "BRAIN_DB": runtime_home / "brain_v12.db",
        "BRAIN_SYNC_QUEUE": runtime_home / "state" / "sync_queue.jsonl",
        "BRAIN_GIT_ROOT": runtime_home / "brain_git_data",
        "BRAIN_EVIDENCE_DB": runtime_home / "brain6_artifacts" / "evidence" / "evidence.db",
        "AGENT_SANDBOX": runtime_home / "agent_sandbox",
        "BRAIN_SUPERVISOR_ROOT": runtime_home / "brain6_artifacts" / "supervisor",
        "BRAIN_SUCCESS_BOT_ROOT": runtime_home / "brain6_artifacts" / "success_bot",
    }
    migrators = {
        "BRAIN_DB": _copy_sqlite_if_missing,
        "BRAIN_SYNC_QUEUE": _copy_file_if_missing,
        "BRAIN_GIT_ROOT": _copy_tree_if_missing,
        "BRAIN_EVIDENCE_DB": _copy_sqlite_if_missing,
        "AGENT_SANDBOX": _copy_tree_if_missing,
        "BRAIN_SUPERVISOR_ROOT": _copy_tree_if_missing,
        "BRAIN_SUCCESS_BOT_ROOT": _copy_tree_if_missing,
    }
    for name, default_path in defaults.items():
        os.environ.setdefault(name, str(default_path.resolve()))
        if name not in explicit:
            migrators[name](legacy[name], Path(os.environ[name]).expanduser().resolve())

    # Keep legacy media available as read-only inputs, but write new renders under
    # the runtime home so app import never needs to create directories in the checkout.
    legacy_media = source / "web" / "media"
    runtime_media = runtime_home / "media"
    if "BRAIN_MEDIA_ROOT" not in explicit:
        # Media endpoints write uploads, visual scenes and generated images to this
        # root, so never default it to a possibly read-only source-tree directory.
        _copy_tree_if_missing(legacy_media, runtime_media)
        media_root = runtime_media
        os.environ.setdefault("BRAIN_MEDIA_ROOT", str(media_root.resolve()))
    else:
        media_root = Path(os.environ["BRAIN_MEDIA_ROOT"]).expanduser().resolve()

    default_output = (
        media_root / "engine"
        if "BRAIN_MEDIA_ROOT" in explicit and "BRAIN_MEDIA_OUTPUT_ROOT" not in explicit
        else runtime_home / "media" / "engine"
    )
    os.environ.setdefault("BRAIN_MEDIA_OUTPUT_ROOT", str(default_output.resolve()))
    return runtime_home
