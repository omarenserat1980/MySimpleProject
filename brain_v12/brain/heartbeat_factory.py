"""Durable, zero-network heartbeat protocol core for Electronic Brain V12.

This module is deliberately a registry/protocol primitive, not a background
scheduler and not proof of remote delivery. Transport adapters must explicitly
record SENT and ACKNOWLEDGED; VERIFIED requires a separate evidence reference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
HEARTBEAT_STATES = frozenset({
    "CREATED", "SENT", "ACKNOWLEDGED", "VERIFIED", "DELAYED",
    "FAILED", "REJECTED", "UNKNOWN",
})
MODES = frozenset({"local", "test", "remote", "simulated"})
_SECRET_KEY = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential|private[_-]?key)", re.I)


def utc_iso(timestamp: float | None = None) -> str:
    return datetime.fromtimestamp(
        time.time() if timestamp is None else float(timestamp), timezone.utc
    ).isoformat()


def _json_safe(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _safe_error_code(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    # Only stable classification codes are persisted, never arbitrary exception text.
    return candidate if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", candidate) else "UNCLASSIFIED_ERROR"


def redact(value: Any) -> Any:
    """Recursively redact secret-like keys before anything reaches evidence."""
    if isinstance(value, dict):
        return {
            str(k): ("[REDACTED]" if _SECRET_KEY.search(str(k)) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return f"[UNSERIALIZABLE:{type(value).__name__}]"


@dataclass(frozen=True)
class FunctionDefinition:
    function_id: str
    name: str
    category: str
    owner: str = "brain"
    implementation: str = "protocol_only"
    interval_seconds: int = 60
    timeout_seconds: int = 10
    max_concurrency: int = 1
    auth_required: bool = False
    enabled: bool = False
    source_of_truth: str = "not_configured"
    resource_limit: str = "bounded"
    retry_limit: int = 2

    def validate(self) -> None:
        if not self.function_id.strip() or not self.name.strip() or not self.category.strip():
            raise ValueError("FUNCTION_ID_NAME_CATEGORY_REQUIRED")
        if self.interval_seconds < 5:
            raise ValueError("INTERVAL_BELOW_SAFE_MINIMUM")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("TIMEOUT_OUT_OF_RANGE")
        if not 1 <= self.max_concurrency <= 32:
            raise ValueError("MAX_CONCURRENCY_OUT_OF_RANGE")
        if not 0 <= self.retry_limit <= 5:
            raise ValueError("RETRY_LIMIT_OUT_OF_RANGE")


class HeartbeatConflict(ValueError):
    """A duplicate identifier was reused with incompatible content."""


class HeartbeatFactory:
    """SQLite-backed function registry and explicit heartbeat state machine.

    No scheduler, remote sender, worker launcher, or production side effect is
    started by constructing this object. All times are UTC epoch seconds.
    """

    def __init__(self, path: str | os.PathLike[str] = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            expanded = Path(self.path).expanduser()
            expanded.resolve().parent.mkdir(parents=True, exist_ok=True)
            self.path = str(expanded)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        if self.path != ":memory:":
            self.db.execute("PRAGMA journal_mode=WAL")
        self._initialize()

    def close(self) -> None:
        self.db.close()

    def _initialize(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS heartbeat_functions (
            function_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            owner TEXT NOT NULL,
            implementation TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL CHECK(interval_seconds >= 5),
            timeout_seconds INTEGER NOT NULL CHECK(timeout_seconds BETWEEN 1 AND 300),
            max_concurrency INTEGER NOT NULL CHECK(max_concurrency BETWEEN 1 AND 32),
            auth_required INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            source_of_truth TEXT NOT NULL,
            resource_limit TEXT NOT NULL,
            retry_limit INTEGER NOT NULL,
            status TEXT NOT NULL,
            last_attempt_at REAL,
            last_success_at REAL,
            last_error_code TEXT,
            evidence_ref TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS heartbeat_events (
            heartbeat_id TEXT PRIMARY KEY,
            function_id TEXT NOT NULL REFERENCES heartbeat_functions(function_id),
            worker_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK(sequence > 0),
            schema_version INTEGER NOT NULL,
            generated_at REAL NOT NULL,
            sent_at REAL,
            received_at REAL,
            status TEXT NOT NULL,
            mode TEXT NOT NULL,
            source TEXT NOT NULL,
            latency_ms REAL,
            correlation_id TEXT,
            evidence_ref TEXT,
            error_code TEXT,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            UNIQUE(function_id, worker_id, sequence)
        );
        CREATE INDEX IF NOT EXISTS idx_heartbeat_function_time
            ON heartbeat_events(function_id, generated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_heartbeat_status_time
            ON heartbeat_events(status, generated_at DESC);
        """)

    def register_function(self, definition: FunctionDefinition | dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
        if isinstance(definition, dict):
            definition = FunctionDefinition(**definition)
        definition.validate()
        instant = time.time() if now is None else float(now)
        values = asdict(definition)
        values["schema_version"] = SCHEMA_VERSION
        values["auth_required"] = int(definition.auth_required)
        values["enabled"] = int(definition.enabled)
        existing = self.db.execute(
            "SELECT * FROM heartbeat_functions WHERE function_id=?", (definition.function_id,)
        ).fetchone()
        if existing:
            self.db.execute("""
                UPDATE heartbeat_functions SET name=?,category=?,schema_version=?,owner=?,
                implementation=?,interval_seconds=?,timeout_seconds=?,max_concurrency=?,
                auth_required=?,enabled=?,source_of_truth=?,resource_limit=?,retry_limit=?,
                updated_at=? WHERE function_id=?
            """, (
                definition.name, definition.category, SCHEMA_VERSION, definition.owner,
                definition.implementation, definition.interval_seconds, definition.timeout_seconds,
                definition.max_concurrency, int(definition.auth_required), int(definition.enabled),
                definition.source_of_truth, definition.resource_limit, definition.retry_limit,
                instant, definition.function_id,
            ))
        else:
            self.db.execute("""
                INSERT INTO heartbeat_functions (
                    function_id,name,category,schema_version,owner,implementation,
                    interval_seconds,timeout_seconds,max_concurrency,auth_required,enabled,
                    source_of_truth,resource_limit,retry_limit,status,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                definition.function_id, definition.name, definition.category, SCHEMA_VERSION,
                definition.owner, definition.implementation, definition.interval_seconds,
                definition.timeout_seconds, definition.max_concurrency, int(definition.auth_required),
                int(definition.enabled), definition.source_of_truth, definition.resource_limit,
                definition.retry_limit, "REGISTERED", instant, instant,
            ))
        return self.get_function(definition.function_id)

    def get_function(self, function_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM heartbeat_functions WHERE function_id=?", (function_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_functions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM heartbeat_functions ORDER BY function_id"
        ).fetchall()]

    def create_heartbeat(
        self, function_id: str, *, worker_id: str, node_id: str,
        mode: str = "test", source: str = "local_protocol",
        sequence: int | None = None, correlation_id: str | None = None,
        payload: dict[str, Any] | None = None, now: float | None = None,
        authorization_ref: str | None = None,
    ) -> dict[str, Any]:
        definition = self.get_function(function_id)
        if definition is None:
            raise KeyError("FUNCTION_NOT_REGISTERED")
        if not definition["enabled"]:
            raise RuntimeError("FUNCTION_DISABLED")
        if not worker_id.strip() or not node_id.strip():
            raise ValueError("WORKER_AND_NODE_ID_REQUIRED")
        if mode not in MODES:
            raise ValueError("HEARTBEAT_MODE_INVALID")
        if definition["auth_required"] and not (authorization_ref and authorization_ref.strip()):
            raise PermissionError("AUTHORIZATION_REFERENCE_REQUIRED")
        instant = time.time() if now is None else float(now)
        if sequence is None:
            row = self.db.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 AS n FROM heartbeat_events WHERE function_id=? AND worker_id=?",
                (function_id, worker_id),
            ).fetchone()
            sequence = int(row["n"])
        if int(sequence) < 1:
            raise ValueError("SEQUENCE_MUST_BE_POSITIVE")
        heartbeat_id = f"hb-{function_id}-{worker_id}-{int(sequence)}"
        safe_payload = redact(payload or {})
        raw = _json_safe(safe_payload)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        try:
            self.db.execute("""
                INSERT INTO heartbeat_events (
                    heartbeat_id,function_id,worker_id,node_id,sequence,schema_version,
                    generated_at,status,mode,source,correlation_id,payload_json,payload_sha256
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (heartbeat_id, function_id, worker_id, node_id, int(sequence), SCHEMA_VERSION,
                  instant, "CREATED", mode, source[:120], correlation_id, raw, digest))
        except sqlite3.IntegrityError as exc:
            existing = self.db.execute(
                "SELECT payload_sha256,node_id,mode,source,correlation_id FROM heartbeat_events WHERE heartbeat_id=?",
                (heartbeat_id,),
            ).fetchone()
            if (existing and existing["payload_sha256"] == digest
                    and existing["node_id"] == node_id and existing["mode"] == mode
                    and existing["source"] == source[:120]
                    and existing["correlation_id"] == correlation_id):
                return self.get_heartbeat(heartbeat_id)
            raise HeartbeatConflict("HEARTBEAT_ID_OR_SEQUENCE_CONFLICT") from exc
        self.db.execute(
            "UPDATE heartbeat_functions SET status='CREATED',last_attempt_at=?,updated_at=? WHERE function_id=?",
            (instant, instant, function_id),
        )
        return self.get_heartbeat(heartbeat_id)

    def get_heartbeat(self, heartbeat_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM heartbeat_events WHERE heartbeat_id=?", (heartbeat_id,)
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def transition(self, heartbeat_id: str, target: str, *, now: float | None = None,
                   evidence_ref: str | None = None, error_code: str | None = None,
                   latency_ms: float | None = None) -> dict[str, Any]:
        if target not in HEARTBEAT_STATES:
            raise ValueError("HEARTBEAT_STATUS_INVALID")
        instant = time.time() if now is None else float(now)
        item = self.get_heartbeat(heartbeat_id)
        if item is None:
            raise KeyError("HEARTBEAT_NOT_FOUND")
        allowed = {
            "CREATED": {"SENT", "FAILED", "REJECTED", "UNKNOWN"},
            "SENT": {"ACKNOWLEDGED", "DELAYED", "FAILED", "REJECTED", "UNKNOWN"},
            "ACKNOWLEDGED": {"VERIFIED", "FAILED", "UNKNOWN"},
            "DELAYED": {"SENT", "FAILED", "UNKNOWN"},
            "UNKNOWN": {"ACKNOWLEDGED", "FAILED", "REJECTED"},
            "VERIFIED": set(), "FAILED": set(), "REJECTED": set(),
        }
        if target == item["status"]:
            return item
        if target not in allowed[item["status"]]:
            raise ValueError(f"INVALID_HEARTBEAT_TRANSITION:{item['status']}->{target}")
        if target == "VERIFIED" and not (evidence_ref and evidence_ref.strip()):
            raise ValueError("VERIFICATION_EVIDENCE_REQUIRED")
        if target == "SENT" and item["sent_at"] is not None and item["status"] != "DELAYED":
            raise ValueError("HEARTBEAT_ALREADY_SENT")
        sent_at = instant if target == "SENT" else item["sent_at"]
        received_at = instant if target == "ACKNOWLEDGED" else item["received_at"]
        safe_error_code = _safe_error_code(error_code)
        self.db.execute("""
            UPDATE heartbeat_events SET status=?,sent_at=?,received_at=?,
              evidence_ref=COALESCE(?,evidence_ref),error_code=?,latency_ms=COALESCE(?,latency_ms)
            WHERE heartbeat_id=?
        """, (target, sent_at, received_at, evidence_ref, safe_error_code, latency_ms, heartbeat_id))
        success_at = instant if target == "VERIFIED" else None
        function_status = target
        self.db.execute("""
            UPDATE heartbeat_functions SET status=?,last_success_at=COALESCE(?,last_success_at),
              last_error_code=?,evidence_ref=COALESCE(?,evidence_ref),updated_at=?
            WHERE function_id=?
        """, (function_status, success_at, safe_error_code, evidence_ref, instant, item["function_id"]))
        return self.get_heartbeat(heartbeat_id)

    def delayed_functions(self, *, now: float | None = None) -> list[dict[str, Any]]:
        instant = time.time() if now is None else float(now)
        output = []
        for function in self.list_functions():
            if not function["enabled"]:
                continue
            last = function["last_success_at"]
            reference = last if last is not None else function["created_at"]
            age = instant - float(reference)
            if age > int(function["interval_seconds"]):
                output.append({
                    "function_id": function["function_id"],
                    "status": "DELAYED",
                    "age_seconds": max(0.0, age),
                    "interval_seconds": function["interval_seconds"],
                    "source_of_truth": function["source_of_truth"],
                })
        return output

    def summary(self) -> dict[str, Any]:
        function_rows = self.list_functions()
        states = {state: 0 for state in sorted(HEARTBEAT_STATES)}
        for row in self.db.execute("SELECT status,COUNT(*) AS n FROM heartbeat_events GROUP BY status"):
            states[row["status"]] = row["n"]
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "local_protocol_only",
            "functions_registered": len(function_rows),
            "functions_enabled": sum(bool(x["enabled"]) for x in function_rows),
            "functions_with_runtime_adapter": sum(x["implementation"] != "protocol_only" for x in function_rows),
            "heartbeats_total": sum(states.values()),
            "heartbeat_states": states,
            "delayed_functions": len(self.delayed_functions()),
            "scheduler_running": False,
            "remote_delivery_proven": False,
        }
