"""Execute configured external benchmark adapters and record evidence."""
from __future__ import annotations
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from cloud.cognitive_benchmark_registry import BenchmarkStatus, get_benchmarks

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "STATE" / "benchmarks"

def _command(entrypoint: str):
    raw = os.environ.get(entrypoint, "").strip()
    if not raw:
        return None
    parts = shlex.split(raw)
    if not parts or not (shutil.which(parts[0]) or Path(parts[0]).exists()):
        return None
    return parts

def run_one(spec):
    command = _command(spec.local_entrypoint)
    result = {"benchmark": spec.name, "key": spec.key, "capability": spec.capability,
              "status": BenchmarkStatus.NOT_CONFIGURED.value, "score": None,
              "official_source": spec.official_source, "protocol": spec.protocol,
              "external_official_eval_required": spec.requires_external_eval,
              "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    if command is None:
        result["evidence"] = "No executable adapter configured; no score claimed."
        return result
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=3600)
    result["status"] = BenchmarkStatus.PASS.value if proc.returncode == 0 else BenchmarkStatus.FAIL.value
    result["exit_code"] = proc.returncode
    result["stdout_tail"] = proc.stdout[-4000:]
    result["stderr_tail"] = proc.stderr[-4000:]
    result["evidence"] = "Adapter executed; score must be emitted by the adapter with provenance."
    return result

def run_all():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_one(spec) for spec in get_benchmarks()]
    manifest = {"generated_utc": datetime.now(timezone.utc).isoformat(),
                "results": results,
                "policy": "Null score means unmeasured; no benchmark score is fabricated."}
    (EVIDENCE_DIR / "latest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return results

def main():
    for result in run_all():
        print(f"{result['key']}={result['status']} score={result['score']}")

if __name__ == "__main__":
    main()
