"""Evidence-backed, bounded self-improvement telemetry for Brain tool invocations.

Every invocation is observed. This module never executes generated code or mutates
tool implementations automatically: it records redacted outcomes and maintains
actionable improvement proposals for review through the normal verification gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_LOCK = threading.Lock()
_SECRET_KEY = re.compile(r"(secret|token|password|passwd|api[_-]?key|authorization|credential|private[_-]?key)", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_dir() -> Path:
    runtime = os.getenv("BRAIN_RUNTIME_HOME")
    base = Path(runtime).expanduser() if runtime else Path(__file__).resolve().parents[2]
    return base / ".brain" / "state" / "tool_evolution"


def _safe_params_shape(params: Any) -> dict[str, Any]:
    """Record parameter names/types only; never persist values."""
    if not isinstance(params, dict):
        return {"type": type(params).__name__}
    shape: dict[str, Any] = {}
    for key, value in sorted(params.items()):
        if _SECRET_KEY.search(str(key)):
            shape[str(key)] = "[REDACTED_FIELD]"
        elif isinstance(value, dict):
            shape[str(key)] = {"type": "object", "keys": sorted(str(k) for k in value)[:40]}
        elif isinstance(value, list):
            shape[str(key)] = {"type": "array", "length": min(len(value), 1000)}
        else:
            shape[str(key)] = {"type": type(value).__name__}
    return shape


def _signature(tool_name: str, status: str, error_code: str | None) -> str:
    raw = json.dumps([tool_name, status, error_code], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def record_invocation(
    tool_name: str,
    status: str,
    params: Any = None,
    duration_ms: float = 0.0,
    error: BaseException | str | None = None,
    risk: str = "low",
    permission: str | None = None,
) -> dict[str, Any]:
    """Persist one redacted observation and refresh a per-tool improvement proposal."""
    name = str(tool_name or "unknown")[:160]
    normalized_status = str(status or "UNKNOWN")[:80].upper()
    error_code = type(error).__name__ if isinstance(error, BaseException) else (
        str(error)[:80] if error else None
    )
    event = {
        "at": _utc_now(),
        "tool": name,
        "status": normalized_status,
        "duration_ms": round(max(0.0, float(duration_ms)), 3),
        "error_code": error_code,
        "risk": str(risk)[:32],
        "permission_required": bool(permission),
        "params_shape": _safe_params_shape(params),
        "signature": _signature(name, normalized_status, error_code),
        "source_mutation": "NEVER_AUTOMATIC",
    }
    directory = _state_dir()
    history = directory / "invocations.jsonl"
    proposals = directory / "improvement_proposals.json"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with history.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            # Bound scan cost; history remains append-only and can be archived separately.
            recent: list[dict[str, Any]] = []
            with history.open("r", encoding="utf-8") as stream:
                lines = stream.readlines()[-500:]
            for line in lines:
                try:
                    item = json.loads(line)
                    if item.get("tool") == name:
                        recent.append(item)
                except (ValueError, TypeError):
                    continue
            failures = [item for item in recent if item.get("status") not in {
                "OK", "EXECUTED", "VERIFIED", "SUCCESS", "UNKNOWN_TOOL"
            }]
            same_failure = [item for item in recent if item.get("signature") == event["signature"]]
            suggestions: list[dict[str, str]] = []
            if normalized_status in {"FAILED", "INVALID_TOOL_RESULT", "TIMEOUT", "ERROR"}:
                suggestions.append({
                    "kind": "failure_reduction",
                    "priority": "high",
                    "action": "Add a regression test for this failure and return a stable machine-readable error code.",
                })
            if len(same_failure) >= 3:
                suggestions.append({
                    "kind": "repeat_failure",
                    "priority": "critical",
                    "action": "Stop identical retries; gather new evidence or select a different approved remediation.",
                })
            if duration_ms >= 5000:
                suggestions.append({
                    "kind": "latency",
                    "priority": "medium",
                    "action": "Profile this tool with bounded timeouts and identify the slowest dependency.",
                })
            if normalized_status in {"WAITING_APPROVAL", "WAITING_PERMISSION"}:
                suggestions.append({
                    "kind": "governance",
                    "priority": "medium",
                    "action": "Keep the denial fail-closed; provide the exact permission/approval requirement to the operator.",
                })
            current = {}
            if proposals.exists():
                try:
                    current = json.loads(proposals.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    current = {}
            by_tool = current.get("tools", {}) if isinstance(current, dict) else {}
            by_tool[name] = {
                "last_seen_at": event["at"],
                "invocations_observed": len(recent),
                "non_success_observed": len(failures),
                "last_status": normalized_status,
                "last_duration_ms": event["duration_ms"],
                "improvements": suggestions,
                "policy": "propose_and_verify_before_change",
            }
            payload = {
                "schema_version": 1,
                "updated_at": event["at"],
                "observations_window": "last 500 invocations globally",
                "tools": by_tool,
                "safety": {
                    "source_code_modified": False,
                    "secrets_or_parameter_values_recorded": False,
                    "automatic_privilege_escalation": False,
                },
            }
            temp = proposals.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            temp.replace(proposals)
    except OSError:
        # Telemetry must not crash the user's tool call; caller may expose this status separately.
        return {"recorded": False, "reason": "EVOLUTION_STATE_UNAVAILABLE", "tool": name}
    return {"recorded": True, "tool": name, "status": normalized_status, "improvement_count": len(suggestions)}


def invoke_observed(
    tool_name: str,
    handler: Callable[[dict[str, Any]], Any],
    params: dict[str, Any] | None = None,
    *,
    risk: str = "low",
    permission: str | None = None,
) -> Any:
    """Reusable adapter for tools outside BrainAI as well as registered Brain tools."""
    started = time.monotonic()
    error: BaseException | None = None
    status = "OK"
    try:
        result = handler(params or {})
        if isinstance(result, dict) and result.get("ok") is False:
            status = str(result.get("status") or "FAILED")
        return result
    except BaseException as exc:
        error = exc
        status = "FAILED"
        raise
    finally:
        record_invocation(
            tool_name, status, params=params,
            duration_ms=(time.monotonic() - started) * 1000,
            error=error, risk=risk, permission=permission,
        )
