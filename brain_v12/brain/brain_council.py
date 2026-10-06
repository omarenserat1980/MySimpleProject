"""Brain Council: Brain + ChatGPT + active clients, with durable minutes and bounded execution.

The council is deliberative and evidence-gated:
- ChatGPT advises; Brain decides.
- Minutes are durable.
- Decisions become at most one bounded action per client.
- Unsupported/external side effects remain pending until the proper primary executor and evidence exist.
- New clients are proposals only until explicitly admitted by the customer-scope policy.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrainCouncil:
    def __init__(
        self,
        db_path: str,
        chatgpt_provider: Any,
        decision_engine: Any,
        state_reader: Callable[[str], dict[str, Any]] | None = None,
        action_requester: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        device_reader: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.db_path = db_path
        self.chatgpt_provider = chatgpt_provider
        self.decision_engine = decision_engine
        self.state_reader = state_reader or (lambda _client_id: {})
        self.action_requester = action_requester
        self.device_reader = device_reader or (lambda: {})
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS brain_council_meetings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                participants TEXT NOT NULL,
                agenda TEXT NOT NULL,
                chatgpt_advice TEXT NOT NULL DEFAULT '',
                decisions TEXT NOT NULL DEFAULT '[]',
                execution_results TEXT NOT NULL DEFAULT '[]',
                new_client_proposals TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS brain_council_actions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                client_id TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_required TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            con.commit()

    def _formal_clients(self) -> list[dict[str, Any]]:
        # Keep this aligned with the current two-customer execution contract.
        return [
            {"client_id": "CL-000001", "role": "industrial", "request": "تشغيل ISO على Arkan", "target": "arkan"},
            {"client_id": "CL-000002", "role": "cloud", "request": "تجهيز Windows Server 2025 سحابياً", "target": "brain-cloud"},
            {"client_id": "CL-000003", "role": "revenue", "request": "تحقيق إيراد حقيقي مثبت", "target": "revenue"},
        ]

    def convene(self, title: str = "اجتماع عقل برين والعملاء", agenda: list[str] | None = None) -> dict[str, Any]:
        with self._connect() as con:
            previous = con.execute("SELECT id,status FROM brain_council_meetings ORDER BY id DESC LIMIT 1").fetchone()
        if previous and str(previous["status"]) not in {"VERIFIED"}:
            return {"ok": False, "status": "PREVIOUS_COUNCIL_NOT_CLOSED", "previous_meeting_id": int(previous["id"]), "previous_status": str(previous["status"]), "required_action": "VERIFY_OR_REPAIR_PREVIOUS_MEETING"}
        participants = [
            {"id": "BRAIN", "role": "chair_and_executor"},
            {"id": "CHATGPT", "role": "advisor_and_reviewer"},
            *self._formal_clients(),
        ]
        device = self.device_reader() or {}
        agents = list(device.get("agents") or [])
        preferred = [a for a in agents if str(a.get("agent_id") or "").lower() in {"arkan", "arkan-01", "arkan01"} and a.get("online")]
        online = preferred or [a for a in agents if a.get("online")]
        if online:
            selected = online[0]
            participants.append({"id": str(selected.get("agent_id")), "role": "device_observer_and_execution_endpoint", "online": True, "state": selected.get("state", "ONLINE")})
            device_invitation = {"included": True, "endpoint": str(selected.get("agent_id")), "reason": "Arkan is online" if selected in preferred else "Arkan unavailable; online Brain Agent selected as fallback"}
        else:
            participants.append({"id": "DEVICE_UNAVAILABLE", "role": "device_observer", "online": False, "state": "NO_ONLINE_AGENT"})
            device_invitation = {"included": False, "endpoint": None, "reason": "No online Arkan or replacement Brain Agent"}
        states = []
        for client in self._formal_clients():
            state = self.state_reader(client["client_id"]) or {}
            states.append({**client, "state": state})

        meeting_agenda = agenda or [
            "مراجعة حالة كل عميل وطلبه الحالي",
            "تحديد أول عائق قابل للعلاج",
            "اختيار قرار واحد قابل للتنفيذ لكل عميل عند السماح",
            "تحديد الأدلة المطلوبة لإغلاق القرار",
            "فحص الحاجة الحقيقية لعميل جديد",
        ]
        context = json.dumps({"participants": participants, "clients": states, "agenda": meeting_agenda},
                             ensure_ascii=False, sort_keys=True)
        advice = self.chatgpt_provider.respond(
            user_text=f"اجتماع مجلس Electronic Brain. حلل الوقائع التالية وقدّم توصيات واحدة لكل عميل، وحدد إن كان هناك احتياج مبرر لعميل جديد. لا تعتبر التوصية تنفيذاً ولا تعتبر الإيراد مثبتاً دون دليل خارجي.\n{context}",
            instructions="أنت مستشار ChatGPT في اجتماع رسمي. افصل بين الوقائع والرأي والقرار. لا تختلق نجاحاً أو إيراداً أو عميلاً. اجعل توصياتك قابلة للتحقق."
        )
        stamp = _now()
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO brain_council_meetings(title,status,participants,agenda,chatgpt_advice,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (title, "CONVENED", json.dumps(participants, ensure_ascii=False),
                 json.dumps(meeting_agenda, ensure_ascii=False),
                 str(advice.get("reply") or "")[:20000], stamp, stamp),
            )
            meeting_id = cur.lastrowid
            con.commit()
        return {
            "ok": True,
            "meeting_id": meeting_id,
            "status": "CONVENED",
            "participants": participants,
            "agenda": meeting_agenda,
            "client_states": states,
            "chatgpt": advice,
            "device_invitation": device_invitation,
            "device_status": device,
            "execution_policy": "ONE_BOUNDED_ACTION_PER_CLIENT_THROUGH_EXISTING_PRIMARY_PIPELINE",
            "new_client_policy": "PROPOSAL_ONLY_UNTIL_EXPLICIT_ADMISSION",
        }

    def verify_device_presence(self, meeting_id: int) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_council_meetings WHERE id=?", (int(meeting_id),)).fetchone()
        if not row:
            return {"ok": False, "status": "MEETING_NOT_FOUND"}
        device = self.device_reader() or {}
        agents = list(device.get("agents") or [])
        online = [a for a in agents if a.get("online")]
        arkan = [a for a in online if str(a.get("agent_id") or "").lower() in {"arkan", "arkan-01", "arkan01"}]
        selected = arkan[0] if arkan else (online[0] if online else None)
        presence = {
            "present": bool(selected),
            "agent_id": str(selected.get("agent_id")) if selected else None,
            "state": selected.get("state") if selected else "NO_ONLINE_AGENT",
            "online": bool(selected),
            "preferred_arkan": bool(arkan),
            "checked_at": _now(),
            "ttl_seconds": device.get("ttl_seconds"),
        }
        with self._connect() as con:
            participants = json.loads(row["participants"] or "[]")
            participants = [p for p in participants if p.get("role") != "device_observer_and_execution_endpoint"]
            if selected:
                participants.append({
                    "id": str(selected.get("agent_id")),
                    "role": "device_observer_and_execution_endpoint",
                    "online": True,
                    "state": selected.get("state", "ONLINE"),
                    "presence_checked_at": presence["checked_at"],
                })
            con.execute(
                "UPDATE brain_council_meetings SET participants=?,updated_at=? WHERE id=?",
                (json.dumps(participants, ensure_ascii=False), _now(), int(meeting_id)),
            )
            con.commit()
        return {"ok": True, "meeting_id": int(meeting_id), "status": "DEVICE_PRESENT" if selected else "DEVICE_UNAVAILABLE", "presence": presence}

    def execute_minutes(self, meeting_id: int) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_council_meetings WHERE id=?", (int(meeting_id),)).fetchone()
        if not row:
            return {"ok": False, "status": "MEETING_NOT_FOUND"}
        if str(row["status"]) == "MINUTES_EXECUTED":
            return {
                "ok": True,
                "meeting_id": int(meeting_id),
                "status": "ALREADY_EXECUTED",
                "execution_results": json.loads(row["execution_results"] or "[]"),
                "decisions": json.loads(row["decisions"] or "[]"),
                "new_client_proposals": json.loads(row["new_client_proposals"] or "[]"),
                "no_duplicate_execution": True,
            }

        decisions = []
        results = []
        proposals = []
        for client in self._formal_clients():
            client_id = client["client_id"]
            goal = client["request"]
            options = self.decision_engine.generate(goal)
            decision = self.decision_engine.choose(goal, options, permissions=set())
            decisions.append({"client_id": client_id, "decision": decision})
            selected = decision.get("selected") or {}
            if decision.get("status") != "DECIDED":
                results.append({"client_id": client_id, "status": "DECISION_BLOCKED", "decision": decision})
                continue

            action = {
                "meeting_id": int(meeting_id),
                "client_id": client_id,
                "objective": "EXECUTE_MEETING_DECISION",
                "selected_decision": selected,
                "constraint": "ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE",
                "external_evidence_required": True,
            }
            device = self.device_reader() or {}
            online_agents = [a for a in list(device.get("agents") or []) if a.get("online")]
            arkan_agents = [a for a in online_agents if str(a.get("agent_id") or "").lower() in {"arkan", "arkan-01", "arkan01"}]
            device_endpoint = arkan_agents[0] if arkan_agents else (online_agents[0] if online_agents else None)
            action["device_endpoint"] = str(device_endpoint.get("agent_id")) if device_endpoint else None
            action["device_presence_required"] = bool(device_endpoint)
            if self.action_requester is None:
                result = {"accepted": False, "status": "NO_PRIMARY_ACTION_REQUESTER"}
            elif client_id == "CL-000003":
                result = self.action_requester(client_id, action)
            else:
                # Do not fake execution for industrial/cloud customers. Their
                # existing specialized pipelines remain the only executors.
                result = {
                    "accepted": False,
                    "status": "PRIMARY_PIPELINE_REQUIRED",
                    "reason": "Use the client's existing specialized execution pipeline; council does not create a parallel executor.",
                }
            status = "ACTION_REQUESTED" if result.get("accepted") else str(result.get("status") or "ACTION_NOT_ACCEPTED")
            results.append({"client_id": client_id, "status": status, "action": action, "result": result})
            with self._connect() as con:
                con.execute(
                    "INSERT INTO brain_council_actions(meeting_id,client_id,action,status,evidence_required,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (int(meeting_id), client_id, json.dumps(action, ensure_ascii=False), status,
                     "external execution evidence; payment evidence where revenue is claimed",
                     json.dumps(result, ensure_ascii=False), _now(), _now()),
                )
                con.commit()

        # New-client need is a governance proposal, not automatic admission.
        proposals.append({
            "proposal_id": f"NEW-CLIENT-REVIEW-{meeting_id}",
            "status": "REVIEW_ONLY",
            "reason": "A new client is proposed only if an unmet demand, capacity need, or distinct accountable request cannot be represented by an existing client without violating one-active-request-per-client.",
            "required_fields": [
                "business_need", "requested_outcome", "owner", "capacity_impact",
                "acceptance_evidence", "why_existing_client_cannot_own_request"
            ],
            "admission_gate": "EXPLICIT_GOVERNANCE_APPROVAL",
            "automatic_admission": False,
        })

        with self._connect() as con:
            con.execute(
                "UPDATE brain_council_meetings SET status=?,decisions=?,execution_results=?,new_client_proposals=?,updated_at=? WHERE id=?",
                ("MINUTES_EXECUTED", json.dumps(decisions, ensure_ascii=False),
                 json.dumps(results, ensure_ascii=False), json.dumps(proposals, ensure_ascii=False), _now(), int(meeting_id)),
            )
            con.commit()

        return {
            "ok": True,
            "meeting_id": int(meeting_id),
            "status": "MINUTES_EXECUTED",
            "decisions": decisions,
            "execution_results": results,
            "new_client_proposals": proposals,
            "evidence_required": True,
            "no_fabricated_execution": True,
        }

    def verify_minutes(self, meeting_id: int) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_council_meetings WHERE id=?", (int(meeting_id),)).fetchone()
            actions = con.execute("SELECT * FROM brain_council_actions WHERE meeting_id=? ORDER BY id", (int(meeting_id),)).fetchall()
        if not row:
            return {"ok": False, "status": "MEETING_NOT_FOUND"}
        if str(row["status"]) == "VERIFIED":
            return {"ok": True, "status": "ALREADY_VERIFIED", "meeting_id": int(meeting_id), "no_duplicate_verification": True}
        if str(row["status"]) != "MINUTES_EXECUTED":
            return {"ok": False, "status": "VERIFICATION_NOT_READY", "meeting_id": int(meeting_id), "meeting_status": str(row["status"])}
        results = []
        verified = 0
        pending = 0
        blocked = 0
        for action_row in actions:
            client_id = str(action_row["client_id"])
            state = self.state_reader(client_id) or {}
            recorded = json.loads(action_row["result"] or "{}")
            status = "PENDING_EXTERNAL_EVIDENCE"
            evidence = {"client_id": client_id, "state": state, "recorded_request": recorded}
            if client_id == "CL-000003":
                income = state.get("income") if isinstance(state, dict) else {}
                verified_revenue = float((income or {}).get("verified_revenue_jod", 0) or 0)
                payment_evidence = bool((income or {}).get("payment_evidence"))
                if payment_evidence and verified_revenue > 0:
                    status = "VERIFIED"
                elif recorded.get("accepted") is False:
                    status = "BLOCKED"
            else:
                industrial = state.get("industrial_request") if isinstance(state, dict) else {}
                request_status = str((industrial or {}).get("status") or "").upper()
                if request_status in {"COMPLETED", "VERIFIED", "VERIFIED_COMPLETED"}:
                    status = "VERIFIED"
                elif request_status in {"FAILED", "BLOCKED", "ERROR"}:
                    status = "BLOCKED"
            if status == "VERIFIED":
                verified += 1
            elif status == "BLOCKED":
                blocked += 1
            else:
                pending += 1
            con_status = status
            with self._connect() as con:
                con.execute("UPDATE brain_council_actions SET status=?,result=?,updated_at=? WHERE id=?",
                            (con_status, json.dumps(evidence, ensure_ascii=False), _now(), int(action_row["id"])))
                con.commit()
            results.append({"action_id": int(action_row["id"]), "client_id": client_id, "status": status, "evidence": evidence})
        if blocked:
            meeting_status = "REQUIRES_REPAIR"
        elif pending:
            meeting_status = "PENDING_VERIFICATION"
        else:
            meeting_status = "VERIFIED"
        with self._connect() as con:
            con.execute("UPDATE brain_council_meetings SET status=?,execution_results=?,updated_at=? WHERE id=?",
                        (meeting_status, json.dumps(results, ensure_ascii=False), _now(), int(meeting_id)))
            con.commit()
        return {
            "ok": True,
            "meeting_id": int(meeting_id),
            "status": meeting_status,
            "verified_actions": verified,
            "pending_actions": pending,
            "blocked_actions": blocked,
            "results": results,
            "next_council_allowed": meeting_status == "VERIFIED",
        }

    def minutes(self, meeting_id: int) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_council_meetings WHERE id=?", (int(meeting_id),)).fetchone()
            actions = con.execute("SELECT * FROM brain_council_actions WHERE meeting_id=? ORDER BY id", (int(meeting_id),)).fetchall()
        if not row:
            return {"ok": False, "status": "MEETING_NOT_FOUND"}
        out = dict(row)
        for key in ("participants", "agenda", "decisions", "execution_results", "new_client_proposals"):
            try:
                out[key] = json.loads(out[key] or "[]" if key != "participants" else out[key] or "[]")
            except Exception:
                out[key] = [] if key != "chatgpt_advice" else out[key]
        out["actions"] = [dict(x) for x in actions]
        return {"ok": True, "meeting": out}
