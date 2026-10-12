"""Client 3 suggestion bridge: client -> Brain -> ChatGPT -> decision -> one bounded action.

Fail-closed: advice is not execution, ChatGPT output is not evidence, and no revenue is credited without external payment evidence.
"""
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from typing import Any

def _now():
    return datetime.now(timezone.utc).isoformat()

class ClientSuggestionBridge:
    def __init__(self, db_path: str, chatgpt_provider: Any, decision_engine: Any, action_requester: Any):
        self.db_path, self.chatgpt_provider = db_path, chatgpt_provider
        self.decision_engine, self.action_requester = decision_engine, action_requester
        self._init()

    def _connect(self):
        con=sqlite3.connect(self.db_path); con.row_factory=sqlite3.Row; return con

    def _init(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS client_suggestions(
              id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL,
              suggestion TEXT NOT NULL, chatgpt_advice TEXT NOT NULL DEFAULT '',
              decision TEXT NOT NULL DEFAULT '{}', action_result TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_client_suggestions_client ON client_suggestions(client_id,id)")
            con.commit()

    def submit(self, client_id: str, suggestion: str, context: dict[str, Any] | None = None):
        client_id, suggestion = str(client_id).strip(), str(suggestion).strip()
        if not client_id or not suggestion:
            return {"ok":False,"status":"INVALID_SUGGESTION"}
        if client_id != "CL-000003":
            return {"ok":False,"status":"CLIENT_NOT_IN_SUGGESTION_BRIDGE"}
        gate=self.can_accept_next(client_id)
        if not gate.get("allowed"):
            return {"ok":True,"status":"WAITING_FOR_PREVIOUS_VERIFICATION","client_id":client_id,"gate":gate}
        stamp=_now()
        with self._connect() as con:
            cur=con.execute("INSERT INTO client_suggestions(client_id,suggestion,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                            (client_id,suggestion,"RECEIVED",stamp,stamp))
            sid=cur.lastrowid; con.commit()
        ctx=json.dumps(context or {},ensure_ascii=False,sort_keys=True)
        advice=self.chatgpt_provider.respond(
            user_text=f"حلل اقتراح العميل 3 ضمن Electronic Brain وقدّم توصية عملية واحدة فقط، مع المخاطر والأدلة المطلوبة. لا تعتبر الاقتراح أو التوصية تنفيذًا أو إيرادًا مثبتًا.\nClient: {client_id}\nSuggestion: {suggestion}\nContext: {ctx}",
            instructions="أنت مستشار ChatGPT داخل Electronic Brain. حلّل اقتراح العميل 3 وقدّم توصية واحدة قابلة للتحقق. لا تدّعِ تنفيذًا أو دفعًا أو إيرادًا. إذا كانت البيانات غير كافية فصرّح بذلك."
        )
        if not advice.get("ok"):
            self._update(sid,"CHATGPT_UNAVAILABLE","",{},advice)
            return {"ok":True,"status":"CHATGPT_UNAVAILABLE","suggestion_id":sid,"client_id":client_id,"chatgpt":advice,"execution_allowed":False}
        advice_text=str(advice.get("reply") or "")
        options=self.decision_engine.generate(suggestion)
        # ChatGPT is advisory; Brain decides from governed candidates and permissions.
        decision=self.decision_engine.choose(suggestion,options,permissions=set())
        if decision.get("status")!="DECIDED":
            self._update(sid,"DECISION_BLOCKED",advice_text,decision,{})
            return {"ok":True,"status":"DECISION_BLOCKED","suggestion_id":sid,"client_id":client_id,
                    "chatgpt":{"provider":advice.get("provider"),"model":advice.get("model"),"reply":advice_text},
                    "decision":decision,"execution_allowed":False}
        action={"client_id":client_id,"suggestion_id":sid,"objective":"ADVANCE_CLIENT_SUGGESTION_TOWARD_VERIFIED_OUTCOME",
                "suggestion":suggestion,"chatgpt_recommendation":advice_text[:12000],"brain_decision":decision.get("selected") or {},
                "constraint":"ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE","verified_revenue_only":True,"external_evidence_required":True}
        outcome=self.action_requester(client_id,action)
        if not isinstance(outcome,dict): outcome={"result":outcome}
        status="ACTION_REQUESTED" if outcome.get("accepted") else "ACTION_REJECTED"
        self._update(sid,status,advice_text,decision,outcome)
        return {"ok":True,"status":status,"suggestion_id":sid,"client_id":client_id,
                "chatgpt":{"provider":advice.get("provider"),"model":advice.get("model"),"reply":advice_text},
                "decision":decision,"action":action,"action_result":outcome,
                "execution_policy":"ONE_BOUNDED_ACTION_THROUGH_EXISTING_PRIMARY_PIPELINE",
                "verification_required":True,"revenue_verified":False}

    def _update(self,sid,status,advice,decision,result):
        with self._connect() as con:
            con.execute("UPDATE client_suggestions SET chatgpt_advice=?,decision=?,action_result=?,status=?,updated_at=? WHERE id=?",
                        (advice,json.dumps(decision,ensure_ascii=False),json.dumps(result,ensure_ascii=False),status,_now(),sid))
            con.commit()


    def can_accept_next(self, client_id="CL-000003"):
        """Allow a new suggestion only after the previous action has a fresh outcome."""
        with self._connect() as con:
            row=con.execute("SELECT * FROM client_suggestions WHERE client_id=? ORDER BY id DESC LIMIT 1",(client_id,)).fetchone()
        if not row:
            return {"ok":True,"allowed":True,"reason":"NO_PREVIOUS_SUGGESTION"}
        status=str(row["status"] or "")
        if status in {"RECEIVED","ACTION_REQUESTED"}:
            return {"ok":True,"allowed":False,"reason":"PREVIOUS_SUGGESTION_REQUIRES_VERIFICATION","suggestion_id":row["id"],"status":status}
        return {"ok":True,"allowed":True,"reason":"PREVIOUS_SUGGESTION_RESOLVED","suggestion_id":row["id"],"status":status}

    def reconcile(self, suggestion_id: int, outcome: dict[str, Any]) -> dict[str, Any]:
        """Record one measured outcome, obtain ChatGPT review, and classify the next bounded path."""
        with self._connect() as con:
            row=con.execute("SELECT * FROM client_suggestions WHERE id=? AND client_id='CL-000003'",(int(suggestion_id),)).fetchone()
        if not row:
            return {"ok":False,"status":"SUGGESTION_NOT_FOUND"}
        measured=dict(outcome or {})
        verified=bool(measured.get("payment_verified") and measured.get("payment_evidence"))
        objective_verified=bool(measured.get("objective_verified"))
        if verified:
            next_path="VERIFIED_SUCCESS"
        elif objective_verified:
            next_path="CONTINUE_ONE_BOUNDED_STEP"
        elif measured.get("blocked"):
            next_path="REPAIR_FIRST_BLOCKER"
        else:
            next_path="CHANGE_ONE_BOUNDED_PATH"
        review=self.chatgpt_provider.respond(
            user_text=f"راجع نتيجة اقتراح العميل 3 رقم {suggestion_id}. النتيجة المقاسة: {json.dumps(measured,ensure_ascii=False)}. صنّف الخطوة التالية فقط.",
            instructions="أنت مراجع ChatGPT داخل Electronic Brain. لا تعتبر النجاح مثبتاً إلا بدليل خارجي. اختر: VERIFIED_SUCCESS أو CONTINUE_ONE_BOUNDED_STEP أو REPAIR_FIRST_BLOCKER أو CHANGE_ONE_BOUNDED_PATH. لا تدّعِ تنفيذًا غير مثبت."
        )
        record={"outcome":measured,"payment_verified":verified,"objective_verified":objective_verified,"next_path":next_path,
                "chatgpt_review":str(review.get("reply") or "")[:12000],"reconciled_at":_now()}
        status="VERIFIED_SUCCESS" if verified else "RECONCILED"
        with self._connect() as con:
            con.execute("UPDATE client_suggestions SET action_result=?,status=?,updated_at=? WHERE id=?",
                        (json.dumps(record,ensure_ascii=False),status,_now(),int(suggestion_id)))
            con.commit()
        return {"ok":True,"status":status,"suggestion_id":int(suggestion_id),"client_id":"CL-000003",
                "next_path":next_path,"chatgpt_review":review,"payment_verified":verified,
                "success_requires_payment_evidence":True}
    def history(self,client_id="CL-000003",limit=20):
        with self._connect() as con:
            rows=con.execute("SELECT * FROM client_suggestions WHERE client_id=? ORDER BY id DESC LIMIT ?",(client_id,max(1,min(int(limit),100)))).fetchall()
        out=[]
        for row in rows:
            item=dict(row)
            for k in ("decision","action_result"):
                try:item[k]=json.loads(item[k] or "{}")
                except Exception:item[k]={}
            out.append(item)
        return {"ok":True,"client_id":client_id,"items":out,"count":len(out)}
