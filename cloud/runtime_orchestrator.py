"""Cloud-native Brain runtime orchestrator.

Owns persistent queues, agent stages, cinematic production, storage, verification,
and the YouTube publication boundary. It has no device/Termux dependency.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

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
        if not row:
            return None
        return self._row(row)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db() as c:
            rows = c.execute("SELECT * FROM jobs ORDER BY updated_at DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
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
                row = c.execute(
                    "SELECT * FROM jobs WHERE stage IN ('queued','failed') ORDER BY updated_at LIMIT 1"
                ).fetchone()
            if not row:
                return None
            job = self._row(row)
            try:
                return self._process(job)
            except Exception as exc:
                self._update(job["id"], "failed", {"error": f"{type(exc).__name__}: {exc}"})
                return self.get(job["id"])

    def _process(self, job: dict[str, Any]) -> dict[str, Any]:
        jid, payload = job["id"], job["payload"]
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
        self._update(jid, "planning")
        plan = self._plan(payload)
        self._agent("planner", True)

        self._update(jid, "production", {"plan": plan})
        produced = self._produce(jid, payload, plan)
        self._agent("cinematic", produced.get("ok", False))
        if not produced.get("ok"):
            self._update(jid, "failed", produced)
            return self.get(jid)  # type: ignore[return-value]

        self._update(jid, "verification", produced)
        verification = self._verify(produced)
        self._agent("verifier", verification.get("ok", False))
        if not verification.get("ok"):
            self._update(jid, "failed", verification)
            return self.get(jid)  # type: ignore[return-value]

        result = {**produced, "verification": verification}
        publish_requested = bool(payload.get("publish_youtube"))
        if publish_requested:
            self._update(jid, "publishing", result)
            from cloud.youtube_executor import publish_video
            pub = publish_video(
                video_path=verification["video_path"],
                title=str(payload.get("title", "Brain Cloud Video")),
                description=str(payload.get("description", "")),
                tags=list(payload.get("tags", [])),
                privacy=str(payload.get("privacy", "private")),
            )
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
            "route": "cloud_cinematic_factory",
            "runtime": "brain_cloud",
            "device_required": False,
            "stages": list(self.STAGES),
        }

    def _produce(self, job_id: str, payload: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        out = MEDIA / ("job_" + job_id)
        out.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT),
            "FACTORY_ONE_SHOT": "1",
            "FACTORY_ALLOW_PRODUCTION": "1",
            "FACTORY_REQUIRE_REAL_MEDIA": "1",
            "FACTORY_ALLOW_LOCAL_FALLBACK": os.getenv("FACTORY_ALLOW_LOCAL_FALLBACK", "1"),
            "FACTORY_MEDIA_ROUTE": os.getenv("FACTORY_MEDIA_ROUTE", "local_ffmpeg_cinematic"),
            "FACTORY_DURATION_SECONDS": str(max(1, min(1800, int(payload.get("target_minutes", 12)) * 60))),
            "FACTORY_OUTPUT_DIR": str(out),
            "LOCAL_MEDIA_DIR": str(out),
            "BRAIN_STATE_DIR": str(STATE),
            "FACTORY_STATE_PATH": str(out / "factory_state.json"),
            "FACTORY_PROJECT_MANIFEST": str(out / "cinematic_project_manifest.json"),
            "CINEMA_ENGINE_MANIFEST": str(out / "cinema_engine_v6_manifest.json"),
            "FACTORY_TOPICS_JSON": json.dumps([payload], ensure_ascii=False),
            "FACTORY_OBJECTIVE": plan["objective"],
        })
        log = out / "factory.log"
        with log.open("w", encoding="utf-8") as fh:
            p = subprocess.run(
                ["python", "-m", "brain_v7.braincore_v2.background_factory_worker"],
                cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT,
                timeout=int(os.getenv("BRAIN_FACTORY_TIMEOUT_SECONDS", "3600")),
                check=False,
            )
        video = out / "final.mp4"
        return {"ok": p.returncode == 0 and video.is_file(), "return_code": p.returncode,
                "output_dir": str(out), "video_path": str(video), "log_path": str(log)}

    def _verify(self, produced: dict[str, Any]) -> dict[str, Any]:
        video = Path(produced["video_path"])
        if not video.is_file() or video.stat().st_size < 1024:
            return {"ok": False, "error": "verified MP4 output is missing or too small"}
        probe = shutil.which("ffprobe")
        if not probe:
            return {"ok": False, "error": "ffprobe is required in Brain Cloud"}
        p = subprocess.run([probe, "-v", "error", "-show_entries",
                            "format=duration,size,format_name", "-of", "json", str(video)],
                           capture_output=True, text=True, timeout=60, check=False)
        if p.returncode != 0:
            return {"ok": False, "error": p.stderr[-2000:]}
        try:
            data = json.loads(p.stdout)["format"]
            duration = float(data.get("duration", 0))
            size = int(data.get("size", 0))
        except Exception as exc:
            return {"ok": False, "error": f"invalid ffprobe result: {exc}"}
        if duration <= 0 or size < 1024:
            return {"ok": False, "error": "media QC failed", "probe": data}
        return {"ok": True, "video_path": str(video), "duration": duration, "size": size, "probe": data}

    def snapshot(self) -> dict[str, Any]:
        with self._db() as c:
            queued = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='queued'").fetchone()[0]
            running = c.execute("SELECT COUNT(*) FROM jobs WHERE stage IN ('planning','production','verification','publishing')").fetchone()[0]
            ready = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='ready'").fetchone()[0]
            published = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='published'").fetchone()[0]
            failed = c.execute("SELECT COUNT(*) FROM jobs WHERE stage='failed'").fetchone()[0]
            agents = [dict(x) for x in c.execute("SELECT * FROM agents ORDER BY name").fetchall()]
        return {"runtime": "brain_cloud", "device_required": False, "termux_required": False,
                "queue": {"queued": queued, "running": running, "ready": ready, "published": published, "failed": failed},
                "agents": agents,
                "storage": {"state_dir": str(STATE), "media_dir": str(MEDIA), "queue_db": str(DB),
                            "state_writable": os.access(STATE, os.W_OK), "media_writable": os.access(MEDIA, os.W_OK)}}

    def run_forever(self) -> None:
        sleep_s = max(1, int(os.getenv("BRAIN_QUEUE_POLL_SECONDS", "5")))
        while True:
            item = self.process_one()
            if item is None:
                time.sleep(sleep_s)
