"""Durable, fail-closed mission tracking for the Golden Mission Loop."""
from __future__ import annotations

import json
import os
import smtplib
import sqlite3
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class GoldenMissionController:
    """Persist mission lifecycle; privileged work remains in separately gated executors."""

    def __init__(self, db_path: str | None = None, notifier=None, evidence_store=None):
        self.db_path = db_path or os.getenv(
            "BRAIN_GOLDEN_MISSION_DB",
            str(Path(__file__).resolve().parents[1] / "golden_missions.sqlite3"),
        )
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.notifier = notifier or self._send_email
        self.evidence_store = evidence_store
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS golden_missions (
                    mission_id TEXT PRIMARY KEY, title TEXT NOT NULL, objective TEXT NOT NULL,
                    acceptance_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    estimate_minutes INTEGER NOT NULL, update_interval_minutes INTEGER NOT NULL DEFAULT 15,
                    due_at TEXT NOT NULL, next_update_at TEXT NOT NULL,
                    required_permission TEXT, permission_granted INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
                    evidence_json TEXT NOT NULL DEFAULT '[]', result_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(golden_missions)").fetchall()}
            if "update_interval_minutes" not in columns:
                db.execute("ALTER TABLE golden_missions ADD COLUMN update_interval_minutes INTEGER NOT NULL DEFAULT 15")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _record(row) -> dict[str, Any]:
        out = dict(row)
        out["acceptance"] = json.loads(out.pop("acceptance_json"))
        out["evidence"] = json.loads(out.pop("evidence_json"))
        out["result"] = json.loads(out.pop("result_json"))
        out["permission_granted"] = bool(out["permission_granted"])
        return out

    def create(self, title: str, objective: str, acceptance: list[str],
               estimate_minutes: int = 30, update_minutes: int = 15,
               max_attempts: int = 3) -> dict[str, Any]:
        title, objective = title.strip(), objective.strip()
        acceptance = [str(x).strip() for x in acceptance if str(x).strip()]
        if not title or not objective or not acceptance:
            raise ValueError("MISSION_OBJECTIVE_AND_ACCEPTANCE_REQUIRED")
        if not 1 <= estimate_minutes <= 10080:
            raise ValueError("ESTIMATE_MINUTES_OUT_OF_RANGE")
        if not 1 <= update_minutes <= 1440:
            raise ValueError("UPDATE_INTERVAL_OUT_OF_RANGE")
        if not 1 <= max_attempts <= 10:
            raise ValueError("MAX_ATTEMPTS_OUT_OF_RANGE")
        now = _now()
        mission_id = str(uuid.uuid4())
        due = now + timedelta(minutes=estimate_minutes)
        next_update = min(now + timedelta(minutes=update_minutes), due)
        with self._connect() as db:
            db.execute("""INSERT INTO golden_missions
                (mission_id,title,objective,acceptance_json,status,created_at,estimate_minutes,
                 update_interval_minutes,due_at,next_update_at,max_attempts,evidence_json,result_json,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (mission_id,title,objective,json.dumps(acceptance),"PLANNED",_iso(now),
                 estimate_minutes,update_minutes,_iso(due),_iso(next_update),max_attempts,"[]","{}",_iso(now)))
        self._event(mission_id,"MISSION_CREATED",{"estimate_minutes":estimate_minutes,"due_at":_iso(due),"at":_iso(now)})
        return self.get(mission_id)

    def get(self, mission_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM golden_missions WHERE mission_id=?",(mission_id,)).fetchone()
        if row is None:
            raise KeyError("MISSION_NOT_FOUND")
        return self._record(row)

    def list_due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current = _iso(now or _now())
        with self._connect() as db:
            rows = db.execute("""SELECT * FROM golden_missions
                WHERE status IN ('PLANNED','RUNNING','WAITING_PERMISSION')
                AND next_update_at <= ? ORDER BY next_update_at ASC""",(current,)).fetchall()
        return [self._record(row) for row in rows]

    def start(self, mission_id: str) -> dict[str, Any]:
        mission = self.get(mission_id)
        if mission["required_permission"] and not mission["permission_granted"]:
            raise ValueError("MISSION_PERMISSION_REQUIRED")
        if mission["status"] not in {"PLANNED","RUNNING"}:
            raise ValueError("MISSION_NOT_STARTABLE")
        now = _now()
        self._update(mission_id,status="RUNNING",updated_at=_iso(now),
                     next_update_at=_iso(min(now+timedelta(minutes=mission["update_interval_minutes"]),datetime.fromisoformat(mission["due_at"]))))
        self._event(mission_id,"MISSION_STARTED",{"at":_iso(now)})
        return self.get(mission_id)

    def require_permission(self, mission_id: str, permission: str, detail: str = "") -> dict[str, Any]:
        permission = permission.strip()
        if not permission:
            raise ValueError("PERMISSION_NAME_REQUIRED")
        mission = self.get(mission_id)
        if mission["status"] in {"CLOSED","CANCELLED"}:
            raise ValueError("MISSION_ALREADY_CLOSED")
        now = _now()
        self._update(mission_id,status="WAITING_PERMISSION",required_permission=permission,
                     permission_granted=0,updated_at=_iso(now),next_update_at=_iso(now+timedelta(minutes=mission["update_interval_minutes"])))
        self._event(mission_id,"PERMISSION_REQUIRED",{"permission":permission,"detail":detail[:1000],"at":_iso(now)})
        updated = self.get(mission_id)
        outcome = self.notifier(updated, f"Permission required: {permission}. {detail}"[:2000])
        self._event(mission_id,"PERMISSION_EMAIL_ATTEMPT",outcome if isinstance(outcome,dict) else {"result":str(outcome)})
        return self.get(mission_id)

    def grant_permission(self, mission_id: str, permission: str, approved_by: str) -> dict[str, Any]:
        mission = self.get(mission_id)
        if mission["status"] != "WAITING_PERMISSION":
            raise ValueError("MISSION_NOT_WAITING_FOR_PERMISSION")
        if permission != mission["required_permission"]:
            raise ValueError("PERMISSION_MISMATCH")
        if not approved_by.strip():
            raise ValueError("APPROVER_ID_REQUIRED")
        now = _now()
        self._update(mission_id,permission_granted=1,status="RUNNING",updated_at=_iso(now),
                     next_update_at=_iso(now+timedelta(minutes=mission["update_interval_minutes"])))
        self._event(mission_id,"PERMISSION_GRANTED",{"permission":permission,"approved_by":approved_by[:200],"at":_iso(now)})
        return self.get(mission_id)

    def checkpoint(self, mission_id: str, summary: str, progress: int,
                   next_estimate_minutes: int | None = None,
                   evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        mission = self.get(mission_id)
        if mission["status"] != "RUNNING":
            raise ValueError("MISSION_NOT_RUNNING")
        if not 0 <= progress <= 99:
            raise ValueError("CHECKPOINT_PROGRESS_OUT_OF_RANGE")
        if next_estimate_minutes is not None and not 1 <= next_estimate_minutes <= 10080:
            raise ValueError("ESTIMATE_MINUTES_OUT_OF_RANGE")
        now = _now()
        due = now + timedelta(minutes=next_estimate_minutes) if next_estimate_minutes is not None else datetime.fromisoformat(mission["due_at"])
        update_at = min(now+timedelta(minutes=15),due)
        fields={"due_at":_iso(due),"next_update_at":_iso(update_at),"updated_at":_iso(now)}
        if next_estimate_minutes is not None:
            fields["estimate_minutes"]=next_estimate_minutes
        self._update(mission_id,**fields)
        payload={"summary":summary[:2000],"progress":progress,"at":_iso(now)}
        if evidence:
            payload["evidence"]=evidence
        self._event(mission_id,"CHECKPOINT",payload)
        return self.get(mission_id)

    def notify_due(self, now: datetime | None = None) -> dict[str, Any]:
        """Send due status reminders and advance cadence; never execute mission actions."""
        current = now or _now()
        due = self.list_due(current)
        notified = 0
        failed = 0
        for mission in due:
            message = "Mission update reminder. Status={}; objective={}".format(mission['status'], mission['objective'][:500])
            try:
                outcome = self.notifier(mission, message)
            except Exception as exc:
                outcome = {"sent": False, "reason": type(exc).__name__}
            sent = isinstance(outcome, dict) and outcome.get("sent") is True
            notified += int(sent)
            failed += int(not sent)
            next_update = current + timedelta(minutes=mission["update_interval_minutes"])
            self._update(mission["mission_id"], next_update_at=_iso(next_update), updated_at=_iso(current))
            self._event(mission["mission_id"], "MISSION_UPDATE_REMINDER", {
                "at": _iso(current), "sent": sent,
                "outcome": outcome if isinstance(outcome, dict) else {"result": str(outcome)[:500]},
                "next_update_at": _iso(next_update),
            })
        return {"checked": len(due), "notifications_sent": notified, "notifications_failed_or_unconfigured": failed}

    def record_retry(self, mission_id: str, reason: str) -> dict[str, Any]:
        mission = self.get(mission_id)
        if mission["status"] != "RUNNING":
            raise ValueError("MISSION_NOT_RUNNING")
        now = _now()
        attempts = mission["attempts"] + 1
        if attempts >= mission["max_attempts"]:
            self._update(mission_id,status="BLOCKED",attempts=attempts,updated_at=_iso(now),next_update_at=_iso(now))
            self._event(mission_id,"RETRY_LIMIT_REACHED",{"attempts":attempts,"reason":reason[:1000],"at":_iso(now)})
            outcome = self.notifier(self.get(mission_id),"Mission blocked after retry limit: " + reason[:1000])
            self._event(mission_id,"BLOCKED_EMAIL_ATTEMPT",outcome if isinstance(outcome,dict) else {"result":str(outcome)})
            return self.get(mission_id)
        self._update(mission_id,attempts=attempts,updated_at=_iso(now),
                     next_update_at=_iso(now+timedelta(minutes=mission["update_interval_minutes"])))
        self._event(mission_id,"RETRY_RECORDED",{"attempts":attempts,"reason":reason[:1000],"at":_iso(now)})
        return self.get(mission_id)

    def close(self, mission_id: str, evidence_id: str, evidence_sha256: str, summary: str = "") -> dict[str, Any]:
        mission = self.get(mission_id)
        if mission["status"] != "RUNNING":
            raise ValueError("MISSION_NOT_RUNNING")
        if not self.evidence_store or not evidence_id or not evidence_sha256:
            raise ValueError("VERIFIABLE_EVIDENCE_STORE_REQUIRED")
        item = self.evidence_store.get(evidence_id)
        if not item or item.get("task_id") != mission_id or item.get("sha256") != evidence_sha256:
            raise ValueError("MISSION_EVIDENCE_NOT_FOUND_OR_MISMATCHED")
        verified = self.evidence_store.verify_hash(evidence_id)
        payload = item.get("payload") if isinstance(item.get("payload"),dict) else {}
        criteria = payload.get("criteria_results")
        # Evidence from an earlier retry must never close the current attempt.
        expected_attempt = mission["attempts"] + 1
        attempt_matches = payload.get("attempt_number") == expected_attempt
        # Require an exact, one-to-one pass result for every declared acceptance criterion.
        expected_criteria = mission["acceptance"]
        actual_criteria = [
            entry.get("criterion") for entry in criteria
            if isinstance(entry, dict) and isinstance(entry.get("criterion"), str)
        ] if isinstance(criteria, list) else []
        criteria_pass = (
            isinstance(criteria, list)
            and len(criteria) == len(expected_criteria)
            and len(actual_criteria) == len(expected_criteria)
            and len(set(actual_criteria)) == len(expected_criteria)
            and set(actual_criteria) == set(expected_criteria)
            and all(isinstance(entry, dict) and entry.get("passed") is True for entry in criteria)
        )
        if (not verified.get("ok")
                or payload.get("objective_verified") is not True
                or payload.get("acceptance_passed") is not True
                or not attempt_matches
                or not criteria_pass):
            self._event(mission_id,"CLOSE_REJECTED",{
                "reason":"OBJECTIVE_AND_EVIDENCE_VERIFICATION_REQUIRED",
                "evidence_id":evidence_id,
                "expected_attempt":expected_attempt,
                "evidence_attempt":payload.get("attempt_number"),
            })
            raise ValueError("OBJECTIVE_AND_EVIDENCE_VERIFICATION_REQUIRED")
        result={"objective_verified":True,"evidence_verified":True,"evidence_id":evidence_id,
                "evidence_sha256":evidence_sha256,"attempt_number":expected_attempt,
                "summary":summary[:2000],"criteria_results":criteria}
        now=_now()
        self._update(mission_id,status="CLOSED",result_json=json.dumps(result,ensure_ascii=False),updated_at=_iso(now),next_update_at=_iso(now))
        self._event(mission_id,"GOLDEN_LOOP_CLOSED",{"at":_iso(now),"result":result})
        outcome=self.notifier(self.get(mission_id),"Mission closed successfully with verified objective and evidence.")
        self._event(mission_id,"CLOSURE_EMAIL_ATTEMPT",outcome if isinstance(outcome,dict) else {"result":str(outcome)})
        return self.get(mission_id)

    def _update(self, mission_id: str, **fields):
        allowed={"status","updated_at","next_update_at","due_at","required_permission","permission_granted","attempts","result_json","estimate_minutes"}
        if set(fields)-allowed:
            raise ValueError("INVALID_MISSION_UPDATE")
        assignments=",".join(f"{key}=?" for key in fields)
        with self._connect() as db:
            db.execute(f"UPDATE golden_missions SET {assignments} WHERE mission_id=?",(*fields.values(),mission_id))

    def _event(self, mission_id: str, event: str, payload: dict[str, Any]):
        with self._connect() as db:
            row=db.execute("SELECT evidence_json FROM golden_missions WHERE mission_id=?",(mission_id,)).fetchone()
            if row is None:
                raise KeyError("MISSION_NOT_FOUND")
            evidence=json.loads(row["evidence_json"])
            evidence.append({"event":event,"payload":payload})
            db.execute("UPDATE golden_missions SET evidence_json=?,updated_at=? WHERE mission_id=?",
                       (json.dumps(evidence,ensure_ascii=False),_iso(_now()),mission_id))

    @staticmethod
    def _send_email(mission: dict[str, Any], message: str) -> dict[str, Any]:
        host=os.getenv("BRAIN_SMTP_HOST")
        sender=os.getenv("BRAIN_SMTP_FROM")
        recipient=os.getenv("BRAIN_MISSION_EMAIL_TO")
        if not host or not sender or not recipient:
            return {"sent":False,"reason":"EMAIL_NOT_CONFIGURED","mission_id":mission["mission_id"]}
        email=EmailMessage()
        email["Subject"]=f"[Electronic Brain] {mission['title']} — {mission['status']}"
        email["From"]=sender
        email["To"]=recipient
        email.set_content(f"Mission: {mission['title']}\nID: {mission['mission_id']}\nStatus: {mission['status']}\nObjective: {mission['objective']}\nDue at (UTC): {mission['due_at']}\n\n{message}\n")
        port=int(os.getenv("BRAIN_SMTP_PORT","587"))
        username=os.getenv("BRAIN_SMTP_USERNAME")
        password=os.getenv("BRAIN_SMTP_PASSWORD")
        try:
            with smtplib.SMTP(host,port,timeout=15) as smtp:
                smtp.ehlo()
                if os.getenv("BRAIN_SMTP_STARTTLS","1")=="1":
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if username and password:
                    smtp.login(username,password)
                smtp.send_message(email)
            return {"sent":True,"mission_id":mission["mission_id"]}
        except Exception as exc:
            return {"sent":False,"reason":type(exc).__name__,"mission_id":mission["mission_id"]}
