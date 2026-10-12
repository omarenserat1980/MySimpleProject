"""Verify a golden checkpoint manifest without modifying the checkpoint or runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_checkpoint(manifest_path: str | Path, root: str | Path | None = None) -> dict:
    manifest_file = Path(manifest_path).resolve()
    base = Path(root).resolve() if root is not None else manifest_file.parent
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"schema_version": 1, "status": "INVALID_MANIFEST", "verified": False, "reason": type(exc).__name__}
    entries = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        return {"schema_version": 1, "status": "INVALID_MANIFEST", "verified": False, "reason": "FILES_LIST_REQUIRED"}
    results = []
    for item in entries:
        if not isinstance(item, dict) or not item.get("path") or not item.get("sha256"):
            results.append({"path": str(item.get("path", "")) if isinstance(item, dict) else "", "ok": False, "reason": "INVALID_ENTRY"})
            continue
        path = (base / str(item["path"])).resolve()
        if path != base and base not in path.parents:
            results.append({"path": str(item["path"]), "ok": False, "reason": "PATH_OUTSIDE_ROOT"})
            continue
        if not path.is_file():
            results.append({"path": str(item["path"]), "ok": False, "reason": "FILE_MISSING"})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = str(item["sha256"]).lower()
        results.append({"path": str(item["path"]), "ok": digest == expected, "reason": "PASS" if digest == expected else "HASH_MISMATCH"})
    verified = bool(results) and all(item["ok"] for item in results)
    return {
        "schema_version": 1,
        "status": "CHECKPOINT_VERIFIED" if verified else "CHECKPOINT_INVALID",
        "verified": verified,
        "files_checked": len(results),
        "files_passed": sum(1 for item in results if item["ok"]),
        "results": results,
        "restore_performed": False,
        "source_mutation": "NONE",
    }
