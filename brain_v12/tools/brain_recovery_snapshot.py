#!/usr/bin/env python3
"""Create a safe, deterministic Brain runtime-state snapshot.

The snapshot contains state only; it never reads secret values.
SQLite databases are copied through SQLite's backup API so a live DB can
be snapshotted consistently without stopping the Brain runtime.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, tarfile
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sqlite_backup(src: Path, dst: Path) -> None:
    src_db=sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    try:
        dst_db=sqlite3.connect(dst)
        try:
            src_db.backup(dst_db)
        finally:
            dst_db.close()
    finally:
        src_db.close()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output", default=".brain/recovery/latest")
    ap.add_argument("--source-root", default=".")
    ap.add_argument("--source-commit", default="")
    args=ap.parse_args()

    root=Path(args.source_root).resolve()
    out=Path(args.output).resolve()
    if out == root or root in out.parents:
        raise SystemExit("OUTPUT_MUST_NOT_BE_SOURCE_ROOT")
    out.mkdir(parents=True, exist_ok=True)

    candidates={
        "brain_db": Path(os.getenv("BRAIN_DB", str(root/"brain_v12/brain_v12.db"))),
        "evidence_db": Path(os.getenv("BRAIN_EVIDENCE_DB", str(root/"brain6_artifacts/evidence/evidence.db"))),
        "sync_queue": Path(os.getenv("BRAIN_SYNC_QUEUE", str(root/"brain_v12/.brain/state/sync_queue.jsonl"))),
        "supervisor_history": root/".brain/state/continuous_supervisor.jsonl",
    }

    copied=[]
    for label, src in candidates.items():
        src=src.expanduser()
        if not src.is_absolute():
            src=(root/src).resolve()
        if not src.exists():
            continue
        rel=Path("state")/label
        suffix=".db" if src.suffix==".db" else src.suffix
        dst=out/(str(rel)+suffix)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix==".db":
            sqlite_backup(src,dst)
        else:
            shutil.copy2(src,dst)
        copied.append({"name":label,"source":str(src),"path":str(dst.relative_to(out))})

    commit=args.source_commit.strip()
    if not commit:
        try:
            commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
        except Exception:
            commit="unknown"

    files=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="manifest.json":
            files.append({"path":str(p.relative_to(out)),"bytes":p.stat().st_size,"sha256":sha256(p)})

    manifest={
        "snapshot_format":"brain-runtime-state-v1",
        "created_at":datetime.now(timezone.utc).isoformat(),
        "source_commit":commit,
        "state_files":copied,
        "files":files,
        "secrets_included":False,
        "device_keys_included":False,
        "live_runtime_stopped":False,
        "notes":"Secrets and device keys are intentionally excluded. Restore source from Git checkpoint separately."
    }
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    archive=out.with_suffix(".tar.gz")
    with tarfile.open(archive,"w:gz") as tar:
        tar.add(out,arcname=out.name)
    print(json.dumps({"ok":True,"snapshot":str(out),"archive":str(archive),"source_commit":commit,"files":len(files)},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
