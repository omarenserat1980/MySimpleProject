"""Read-only compute-resource inventory and fail-closed execution policy.

This manager measures the current Python host without probing networks, reading
secret values, starting subprocesses, or enabling mining. It distinguishes
available local CPU/RAM from attested production compute and never authorizes
pool submission or revenue claims.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_BOUNDED_HASHES = 10_000_000
MAX_BOUNDED_SECONDS = 30.0
DEFAULT_BOUNDED_HASHES = 100_000
DEFAULT_BOUNDED_SECONDS = 5.0


def _read_meminfo_available_bytes() -> int | None:
    """Read MemAvailable from procfs when present; return None otherwise."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def _read_cgroup_memory() -> dict[str, int | None]:
    """Read common cgroup v1/v2 memory limits without changing host state."""
    candidates = (
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
         Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")),
    )
    for limit_path, current_path in candidates:
        try:
            limit_text = limit_path.read_text(encoding="ascii").strip()
            current_text = current_path.read_text(encoding="ascii").strip()
            if limit_text == "max":
                return {"limit_bytes": None, "current_bytes": int(current_text)}
            limit, current = int(limit_text), int(current_text)
            # Huge sentinel values in some cgroup v1 hosts mean unlimited.
            if limit >= (1 << 60):
                return {"limit_bytes": None, "current_bytes": current}
            return {"limit_bytes": limit, "current_bytes": current}
        except (OSError, ValueError):
            continue
    return {"limit_bytes": None, "current_bytes": None}


def _available_memory_bytes() -> tuple[int | None, str]:
    host_available = _read_meminfo_available_bytes()
    cgroup = _read_cgroup_memory()
    remaining = None
    if cgroup["limit_bytes"] is not None and cgroup["current_bytes"] is not None:
        remaining = max(0, cgroup["limit_bytes"] - cgroup["current_bytes"])
    known = [value for value in (host_available, remaining) if value is not None]
    if known:
        return min(known), "PROCFS_AND_CGROUP_LOWER_BOUND" if len(known) == 2 else (
            "PROCFS" if host_available is not None else "CGROUP")
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages >= 0 and page_size > 0:
            return pages * page_size, "SYSCONF_ESTIMATE"
    except (AttributeError, OSError, ValueError):
        pass
    return None, "UNAVAILABLE"


def _cpu_affinity_count() -> int | None:
    try:
        affinity = getattr(os, "sched_getaffinity", None)
        return len(affinity(0)) if affinity else None
    except (OSError, NotImplementedError):
        return None


def _runtime_kind() -> str:
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix.lower() or os.environ.get("TERMUX_VERSION"):
        return "ANDROID_TERMUX"
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return "EPHEMERAL_CI_RUNNER"
    return platform.system().upper() or "UNKNOWN"


def build_compute_resource_report(
    *, requested_hashes: int = DEFAULT_BOUNDED_HASHES,
    requested_seconds: float = DEFAULT_BOUNDED_SECONDS,
) -> dict[str, Any]:
    """Return a read-only host inventory and a bounded, non-production plan."""
    if isinstance(requested_hashes, bool) or not isinstance(requested_hashes, int):
        raise ValueError("requested_hashes must be an integer")
    if requested_hashes < 1:
        raise ValueError("requested_hashes must be positive")
    if isinstance(requested_seconds, bool) or not isinstance(requested_seconds, (int, float)):
        raise ValueError("requested_seconds must be numeric")
    if requested_seconds <= 0:
        raise ValueError("requested_seconds must be positive")

    logical = os.cpu_count()
    affinity = _cpu_affinity_count()
    usable_cpus = min(logical, affinity) if logical and affinity else (affinity or logical)
    memory_bytes, memory_source = _available_memory_bytes()
    capped_hashes = min(requested_hashes, MAX_BOUNDED_HASHES)
    capped_seconds = min(float(requested_seconds), MAX_BOUNDED_SECONDS)
    runtime_kind = _runtime_kind()

    return {
        "schema": "brain-compute-resource-report/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "READ_ONLY_LOCAL_RESOURCE_INVENTORY",
        "runtime": {
            "kind": runtime_kind,
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
        },
        "resources": {
            "cpu_logical_count": logical,
            "cpu_affinity_count": affinity,
            "cpu_usable_estimate": usable_cpus,
            "available_memory_bytes_estimate": memory_bytes,
            "memory_evidence_source": memory_source,
        },
        "bounded_compute_plan": {
            "mode": "EXPLICIT_LOCAL_OFFLINE_TEST_ONLY",
            "requested_hashes": requested_hashes,
            "hash_budget": capped_hashes,
            "requested_seconds": float(requested_seconds),
            "time_budget_seconds": capped_seconds,
            "hash_budget_capped": capped_hashes != requested_hashes,
            "time_budget_capped": capped_seconds != float(requested_seconds),
        },
        "execution_gates": {
            "local_bounded_compute_may_be_invoked_explicitly": True,
            "live_mining_authorized": False,
            "host_attestation_verified": False,
            "pool_session_verified": False,
            "share_submission_enabled": False,
            "pool_acceptance_verified": False,
            "revenue_verified": False,
            "production_compute_claim_allowed": False,
        },
        "safety": {
            "network_access_performed": False,
            "subprocesses_started": False,
            "secret_values_read": False,
            "files_modified": False,
            "mining_started": False,
        },
        "interpretation": (
            "CPU and memory values are local runtime estimates only. They do not "
            "prove a stable remote executor, ASIC capability, accepted pool shares, "
            "or profitability. CI runners are ephemeral and are not treated as "
            "persistent mining infrastructure."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hashes", type=int, default=DEFAULT_BOUNDED_HASHES)
    parser.add_argument("--seconds", type=float, default=DEFAULT_BOUNDED_SECONDS)
    parser.add_argument("--output", help="Optional report path; refuses to overwrite.")
    args = parser.parse_args(argv)
    try:
        report = build_compute_resource_report(
            requested_hashes=args.hashes, requested_seconds=args.seconds)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        path = Path(args.output).expanduser().resolve()
        if path.exists():
            parser.error(f"refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
