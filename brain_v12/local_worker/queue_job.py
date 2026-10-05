#!/usr/bin/env python3
"""Create one safe local-worker job without contacting external services."""
from __future__ import annotations
import json, os, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

ALLOWED = {"python_version","platform","brain_home","ffmpeg_version","ffprobe_version","filesystem_probe","brain_ci_verify"}
CI_PROFILES = {"runner_policy", "foundation", "autonomous_pipeline"}
ROOT = Path(os.environ.get("BRAIN_LOCAL_WORKER_ROOT", "brain6_artifacts/local_worker"))
task = sys.argv[1] if len(sys.argv) > 1 else "platform"
if task not in ALLOWED:
    raise SystemExit(f"not_allowlisted:{task}")
params = {}
if task == "brain_ci_verify":
    profile = sys.argv[2] if len(sys.argv) > 2 else ""
    if profile not in CI_PROFILES:
        raise SystemExit(f"ci_profile_not_allowlisted:{profile}")
    params["profile"] = profile
q = ROOT / "queued"; q.mkdir(parents=True, exist_ok=True)
job_id = uuid.uuid4().hex
path = q / f"{job_id}.json"
path.write_text(json.dumps({"job_id": job_id, "task": task, "params": params, "created_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
print(path)
