"""Cloud-native Brain runtime orchestrator with verified film production."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from cloud.film_reliability import FilmReliabilityEngine

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("BRAIN_STATE_DIR", str(ROOT / ".brain_state")))
MEDIA = Path(os.getenv("FACTORY_OUTPUT_DIR", str(ROOT / "cinematic_output")))
DB = STATE / "runtime.db"


def _now() -> float:
    return time.time()


class CloudRuntime:
    STAGES = ("queued", "planning", "production", "verification", "ready", "publishing", "published", "failed")

    def __init__(self) -> None:
        STATE.mkdir(parents=True, exist_ok=True)
        MEDIA.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _db(self) -> sqlite3.Connection:
        c = sqlite3.connect(DB, timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self) -> None:
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, stage TEXT NOT NULL,
                payload TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}',
                attempts INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS jobs_stage_idx ON jobs(stage, updated_at)")
            c.execute("""CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY, status TEXT NOT NULL, last_run REAL NOT NULL,
                runs INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0
            )""")

    def enqueue(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if kind in {"cinematic", "cinematic_autopilot"}:
            payload = dict(payload)
            payload["route"] = "cloud_runtime_reliability_engine"
            payload["production_contract"] = "verified_mp4_v1"
        job_id = uuid.uuid4().hex[:16]
        now = _now()
        with self._db() as c:
            c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                      (job_id, kind, "queued", json.dumps(payload, ensure_ascii=False),
                       "{}", 0, now, now))
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._db() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db() as c:
            rows = c.execute("SELECT * FROM jobs ORDER BY updated_at DESC LIMIT ?",
                             (max(1, min(limit, 200)),)).fetchall()
        return [self._row(r) for r in rows]

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["payload"] = json.loads(d["payload"] or "{}")
        d["result"] = json.loads(d["result"] or "{}")
        return d

    def _update(self, job_id: str, stage: str, result: dict[str, Any] | None = None) -> None:
        with self._db() as c:
            c.execute("UPDATE jobs SET stage=?, result=?, updated_at=?, attempts=attempts+1 WHERE id=?",
                      (stage, json.dumps(result or {}, ensure_ascii=False), _now(), job_id))

    def _agent(self, name: str, ok: bool) -> None:
        with self._db() as c:
            c.execute("""INSERT INTO agents(name,status,last_run,runs,failures)
                         VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET
                         status=excluded.status,last_run=excluded.last_run,
                         runs=agents.runs+1,failures=agents.failures+excluded.failures""",
                      (name, "PASS" if ok else "FAIL", _now(), 1, 0 if ok else 1))

    def process_one(self) -> dict[str, Any] | None:
        with self._lock:
            with self._db() as c:
                c.execute("BEGIN IMMEDIATE")
                row = c.execute(
                    "SELECT * FROM jobs WHERE stage='queued' ORDER BY updated_at LIMIT 1"
                ).fetchone()
                if not row:
                    c.commit()
                    return None
                job_id = row["id"]
                claimed = c.execute(
                    "UPDATE jobs SET stage='planning', updated_at=? WHERE id=? AND stage='queued'",
                    (_now(), job_id),
                ).rowcount
                c.commit()
            if claimed != 1:
                return None
            job = self.get(job_id)
            if not job:
                return None
            try:
                return self._process(job)
            except Exception as exc:
                self._update(job["id"], "failed", {"error": f"{type(exc).__name__}: {exc}"})
                return self.get(job["id"])


    def _process(self, job: dict[str, Any]) -> dict[str, Any]:
        jid, payload = job["id"], job["payload"]
        if job["kind"] == "cinematic_autopilot":
            self._update(jid, "production", {"route": "verified_film_reliability_engine"})
            out = MEDIA / ("autopilot_" + jid)
            engine = FilmReliabilityEngine(out, max_attempts=int(payload.get("max_attempts", 3)))
            result = engine.run(payload)
            self._agent("cinematic_autopilot", result.get("ok", False))
            if result.get("ok"):
                self._update(jid, "ready", result)
            else:
                self._update(jid, "failed", result)
            return self.get(jid)  # type: ignore[return-value]

        if job["kind"] == "youtube_publish":
            self._update(jid, "publishing")
            from cloud.youtube_executor import publish_video
            result = publish_video(
                video_path=str(payload.get("video_path", "")),
                title=str(payload.get("title", "Brain Cloud Video")),
                description=str(payload.get("description", "")),
                tags=list(payload.get("tags", [])),
                privacy=str(payload.get("privacy", "private")),
            )
            self._agent("youtube_publisher", result.get("published", False))
            self._update(jid, "published" if result.get("published") else "failed", {"youtube": result})
            return self.get(jid)  # type: ignore[return-value]

        plan = self._plan(payload)
        self._agent("planner", True)
        self._update(jid, "production", {"plan": plan, "production_contract": "verified_mp4_v1"})
        out = MEDIA / ("job_" + jid)
        produced = FilmReliabilityEngine(out, max_attempts=int(payload.get("max_attempts", 3))).run(payload)
        self._agent("cinematic", produced.get("ok", False))
        if not produced.get("ok"):
            self._update(jid, "failed", produced)
            return self.get(jid)  # type: ignore[return-value]
        self._update(jid, "verification", produced)
        verification = produced["verification"]
        self._agent("verifier", verification.get("ok", False))
        result = {**produced, "verification": verification}
        if not verification.get("ok"):
            self._update(jid, "failed", result)
            return self.get(jid)  # type: ignore[return-value]

        if payload.get("publish_youtube"):
            self._update(jid, "publishing", result)
            from cloud.youtube_executor import publish_video
            pub = publish_video(video_path=verification["video_path"],
                                title=str(payload.get("title", "Brain Cloud Video")),
                                description=str(payload.get("description", "")),
                                tags=list(payload.get("tags", [])),
                                privacy=str(payload.get("privacy", "private")))
            self._agent("youtube_publisher", pub.get("published", False))
            result["youtube"] = pub
            self._update(jid, "published" if pub.get("published") else "failed", result)
        else:
            self._update(jid, "ready", result)
        return self.get(jid)  # type: ignore[return-value]

    def _plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValueError("title is required")
        return {
            "objective": f"Produce and verify: {title}",
            "route": "cloud_film_reliability_engine",
            "runtime": "brain_cloud",
            "device_required": False,
            "termux_required": False,
            "stages": list(self.STAGES),
            "production_contract": "verified_mp4_v1",
        }

    def snapshot(self) -> dict[str, Any]:
        with self._db() as c:
            queued = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='queued'").fetchone()[0]
            running = c.execute("SELECT COUNT(*) FROM jobs WHERE stage IN ('planning','production','verification','publishing')").fetchone()[0]
            ready = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='ready'").fetchone()[0]
            published = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='published'").fetchone()[0]
            failed = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='failed'").fetchone()[0]
            agents = [dict(x) for x in c.execute("SELECT * FROM agents ORDER BY name").fetchall()]
        return {
            "runtime": "brain_cloud",
            "device_required": False,
            "termux_required": False,
            "queue": {"queued": queued, "running": running, "ready": ready, "published": published, "failed": failed},
            "agents": agents,
            "storage": {"state_dir": str(STATE), "media_dir": str(MEDIA), "queue_db": str(DB),
                        "state_writable": os.access(STATE, os.W_OK), "media_writable": os.access(MEDIA, os.W_OK)}
        }

    def run_forever(self) -> None:
        sleep_s = max(1, int(os.getenv("BRAIN_QUEUE_POLL_SECONDS", "5")))
        while True:
            item = self.process_one()
            if item is None:
                time.sleep(sleep_s)
