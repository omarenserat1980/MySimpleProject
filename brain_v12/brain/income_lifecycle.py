"""Controlled opportunity-to-payment lifecycle for Electronic Brain V12.

This module closes the gap between discovering a public opportunity and
claiming that an application, delivery, or payment actually happened.
External actions are evidence-gated: the brain can prepare work, but only
a connected execution channel may produce SUBMITTED/DELIVERING evidence.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import hashlib
import json


class IncomeLifecycle:
    ORDER = (
        "DISCOVERY",
        "QUALIFIED",
        "READY_TO_APPLY",
        "SUBMITTED",
        "CLIENT_RESPONDED",
        "ACCEPTED",
        "DELIVERING",
        "COMPLETED",
        "PAYMENT_VERIFIED",
    )

    EXTERNAL_EVIDENCE = {
        "SUBMITTED": "submission_receipt",
        "CLIENT_RESPONDED": "client_response",
        "ACCEPTED": "acceptance_evidence",
        "DELIVERING": "execution_evidence",
        "COMPLETED": "delivery_evidence",
        "PAYMENT_VERIFIED": "payment_evidence",
    }

    def __init__(self, store):
        self.store = store

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _find(self, opportunity_id):
        rows = self.store.income_opportunities(500)
        return next((x for x in rows if x.get("opportunity_id") == opportunity_id), None)

    def _save(self, row, **updates):
        data = dict(row.get("data") or {})
        data.update(updates)
        data["updated_at"] = self._now()
        self.store.upsert_income_opportunity(data)
        return data

    def _transition(self, opportunity_id, target, evidence="", actor="external_executor"):
        row = self._find(opportunity_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND", "opportunity_id": opportunity_id}
        current = str(row.get("status") or "DISCOVERY")
        if target not in self.ORDER:
            return {"ok": False, "status": "INVALID_TARGET"}
        current_index = self.ORDER.index(current)
        target_index = self.ORDER.index(target)
        if target_index < current_index:
            return {"ok": False, "status": "INVALID_BACKWARD_TRANSITION", "current": current, "target": target}
        if target_index > current_index + 1:
            return {"ok": False, "status": "INVALID_SKIPPED_TRANSITION", "current": current, "target": target}
        if target in self.EXTERNAL_EVIDENCE and not str(evidence).strip():
            return {"ok": False, "status": "EVIDENCE_REQUIRED", "required": self.EXTERNAL_EVIDENCE[target]}
        data = self._save(row, status=target)
        if evidence:
            key = self.EXTERNAL_EVIDENCE.get(target, "evidence")
            data[key] = str(evidence)[:4000]
            self.store.upsert_income_opportunity(data)
        self.store.event("INCOME_LIFECYCLE_TRANSITION", {
            "opportunity_id": opportunity_id, "from": current, "to": target,
            "actor": actor, "evidence_recorded": bool(evidence)
        })
        return {"ok": True, "status": target, "opportunity": data}

    def qualify(self, opportunity_id, notes=""):
        row = self._find(opportunity_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        req = str((row.get("data") or {}).get("requirements") or "")
        url = str(row.get("source_url") or "")
        if not url.startswith(("http://", "https://")) or len(req.strip()) < 8:
            return {"ok": False, "status": "NOT_QUALIFIED", "reason": "MISSING_SOURCE_OR_REQUIREMENTS"}
        return self._transition(opportunity_id, "QUALIFIED", actor="brain")

    def prepare(self, opportunity_id, proposal=""):
        row = self._find(opportunity_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        data = dict(row.get("data") or {})
        title = str(data.get("title") or row.get("title") or "").strip()
        requirements = str(data.get("requirements") or "").strip()
        if not proposal.strip():
            proposal = (
                f"مرحباً، اطلعت على مشروع «{title}». "
                "أستطيع تنفيذ المطلوب بصورة منظمة، مع البدء بفهم المتطلبات ثم تقديم نسخة أولية "
                "للمراجعة قبل التسليم النهائي. "
                f"المتطلبات التي سأبني عليها التنفيذ: {requirements[:900]}"
            )
        fingerprint = hashlib.sha1((opportunity_id + proposal).encode()).hexdigest()[:12]
        data = self._save(row, status="READY_TO_APPLY", proposal=proposal[:6000],
                          proposal_id="PROP-" + fingerprint, prepared_at=self._now(),
                          execution_channel="NOT_CONNECTED")
        self.store.event("INCOME_APPLICATION_PREPARED", {
            "opportunity_id": opportunity_id, "proposal_id": data["proposal_id"]
        })
        return {"ok": True, "status": "READY_TO_APPLY", "opportunity": data,
                "external_submission": "NOT_PERFORMED"}

    def record_external(self, opportunity_id, status, evidence):
        """Record an externally completed step only when its evidence is supplied."""
        return self._transition(opportunity_id, status, evidence=evidence, actor="external_executor")

    def summary(self):
        rows = self.store.income_opportunities(500)
        counts = {s: 0 for s in self.ORDER}
        for row in rows:
            s = str(row.get("status") or "DISCOVERY")
            counts[s] = counts.get(s, 0) + 1
        return {
            "counts": counts,
            "external_execution_ready": False,
            "reason": "لا توجد قناة تنفيذ خارجية متصلة بالحسابات؛ يمكن تجهيز العروض وتسجيل الأدلة فقط.",
            "payment_verified_jod": sum(float(x.get("verified_amount_jod") or 0) for x in rows),
        }
