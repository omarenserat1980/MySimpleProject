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

    def _find(self, opportunity_id, client_id=None):
        rows = self.store.income_opportunities(500, client_id=client_id)
        return next((x for x in rows if x.get("opportunity_id") == opportunity_id), None)

    def _save(self, row, **updates):
        data = dict(row.get("data") or {})
        data.update(updates)
        data["updated_at"] = self._now()
        self.store.upsert_income_opportunity(data)
        return data

    def _transition(self, opportunity_id, target, evidence="", actor="external_executor", client_id=None):
        row = self._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND", "opportunity_id": opportunity_id}
        current = str(row.get("status") or "DISCOVERY")
        if target not in self.ORDER:
            return {"ok": False, "status": "INVALID_TARGET"}
        current_index = self.ORDER.index(current)
        target_index = self.ORDER.index(target)
        if target_index < current_index:
            return {"ok": False, "status": "INVALID_BACKWARD_TRANSITION", "current": current, "target": target}
        allowed_skip = current == "SUBMITTED" and target == "ACCEPTED"
        if target_index > current_index + 1 and not allowed_skip:
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

    def qualify(self, opportunity_id, notes="", client_id=None):
        row = self._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        req = str((row.get("data") or {}).get("requirements") or "")
        url = str(row.get("source_url") or "")
        if not url.startswith(("http://", "https://")) or len(req.strip()) < 8:
            return {"ok": False, "status": "NOT_QUALIFIED", "reason": "MISSING_SOURCE_OR_REQUIREMENTS"}
        return self._transition(opportunity_id, "QUALIFIED", actor="brain", client_id=client_id)

    def prepare(self, opportunity_id, proposal="", client_id=None):
        row = self._find(opportunity_id, client_id=client_id)
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

    def record_external(self, opportunity_id, status, evidence, client_id=None):
        """Record an externally completed step only when its evidence is supplied."""
        return self._transition(opportunity_id, status, evidence=evidence, actor="external_executor", client_id=client_id)

    def request_payment(self, opportunity_id, amount_jod, currency="JOD", client_id=None, order_id=None):
        """Create an auditable payment request after verified delivery."""
        row = self._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        status = str(row.get("status") or "DISCOVERY")
        if status != "COMPLETED":
            return {"ok": False, "status": "DELIVERY_NOT_VERIFIED", "current": status}
        amount = float(amount_jod)
        if amount <= 0:
            return {"ok": False, "status": "INVALID_AMOUNT"}
        data = dict(row.get("data") or {})
        existing = data.get("payment_request") or {}
        if existing:
            if float(existing.get("amount_jod", 0) or 0) == amount and existing.get("currency") == currency:
                return {"ok": True, "status": "ALREADY_REQUESTED", "payment_request": existing}
            return {"ok": False, "status": "PAYMENT_REQUEST_IMMUTABLE"}
        request_id = "PAY-" + hashlib.sha1(
            f"{opportunity_id}|{client_id}|{amount:.2f}|{currency}".encode()
        ).hexdigest()[:12]
        payment_request = {
            "request_id": request_id,
            "opportunity_id": opportunity_id,
            "order_id": order_id,
            "client_id": client_id,
            "amount_jod": round(amount, 2),
            "currency": currency,
            "status": "REQUESTED",
            "created_at": self._now(),
            "payment_provider": "HUMAN_OR_CONNECTED_PROVIDER",
        }
        data = self._save(row, payment_request=payment_request)
        self.store.event("PAYMENT_REQUEST_CREATED", {
            "request_id": request_id,
            "opportunity_id": opportunity_id,
            "amount_jod": round(amount, 2),
        })
        return {"ok": True, "status": "PAYMENT_REQUESTED", "payment_request": payment_request}

    def reconcile_payment(self, opportunity_id, amount_jod, currency, transaction_id, evidence, client_id=None, order_id=None):
        """Reconcile independent payment evidence before revenue recognition."""
        row = self._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        data = dict(row.get("data") or {})
        request = data.get("payment_request") or {}
        if not request:
            return {"ok": False, "status": "PAYMENT_REQUEST_REQUIRED"}
        if order_id and request.get("order_id") and order_id != request.get("order_id"):
            return {"ok": False, "status": "ORDER_MISMATCH"}
        if currency != request.get("currency"):
            return {"ok": False, "status": "CURRENCY_MISMATCH"}
        received = float(amount_jod)
        requested = float(request.get("amount_jod", 0) or 0)
        if received < requested:
            return {"ok": False, "status": "AMOUNT_MISMATCH", "requested": requested, "received": received}
        if not str(transaction_id).strip() or not str(evidence).strip():
            return {"ok": False, "status": "INDEPENDENT_PAYMENT_EVIDENCE_REQUIRED"}
        # Revenue conversion is fail-closed: free-form evidence is not enough.
        # A connected payment authority must explicitly mark the reconciliation
        # as independently verified (normally from a signed provider webhook).
        if not isinstance(evidence, dict) or evidence.get("independent_verification") != "SIGNED_PROVIDER_WEBHOOK":
            return {"ok": False, "status": "SIGNED_PROVIDER_AUTHORITY_REQUIRED"}
        existing = data.get("payment_reconciliation")
        if existing:
            if existing.get("transaction_id") == transaction_id and float(existing.get("received_amount_jod", 0) or 0) == received:
                return {"ok": True, "status": "ALREADY_RECONCILED", "reconciliation": existing}
            return {"ok": False, "status": "PAYMENT_RECONCILIATION_IMMUTABLE"}
        reconciliation = {
            "transaction_id": str(transaction_id)[:300],
            "received_amount_jod": round(received, 2),
            "currency": currency,
            "evidence": str(evidence.get("evidence_ref") or "")[:4000],
            "independent_verification": evidence.get("independent_verification"),
            "provider": str(evidence.get("provider") or "")[:100],
            "event_id": str(evidence.get("event_id") or "")[:200],
            "reconciled_at": self._now(),
            "order_id": order_id or request.get("order_id"),
        }
        data = self._save(row, payment_reconciliation=reconciliation)
        self.store.event("PAYMENT_RECONCILED", {
            "opportunity_id": opportunity_id,
            "transaction_id": str(transaction_id)[:300],
            "received_amount_jod": round(received, 2),
        })
        return {"ok": True, "status": "RECONCILED", "reconciliation": reconciliation}

    def realize_revenue(self, opportunity_id, client_id=None):
        """Recognize revenue only after delivery, payment request, and reconciliation."""
        row = self._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        data = dict(row.get("data") or {})
        if str(data.get("status")) not in {"COMPLETED", "PAYMENT_VERIFIED"}:
            return {"ok": False, "status": "DELIVERY_NOT_VERIFIED"}
        reconciliation = data.get("payment_reconciliation") or {}
        if not reconciliation:
            return {"ok": False, "status": "PAYMENT_NOT_RECONCILED"}
        if data.get("revenue_realized"):
            return {"ok": True, "status": "ALREADY_REALIZED", "amount_jod": float(data.get("verified_amount_jod", 0) or 0)}
        amount = float(reconciliation.get("received_amount_jod", 0) or 0)
        if amount <= 0:
            return {"ok": False, "status": "INVALID_RECONCILED_AMOUNT"}
        data = self._save(row, status="PAYMENT_VERIFIED", verification_status="VERIFIED",
                          verified_amount_jod=amount, revenue_realized=True,
                          revenue_realized_at=self._now())
        self.store.event("REVENUE_REALIZED", {
            "opportunity_id": opportunity_id,
            "amount_jod": amount,
            "transaction_id": reconciliation.get("transaction_id"),
        })
        return {"ok": True, "status": "REVENUE_REALIZED", "amount_jod": amount}

    def summary(self, client_id=None):
        rows = self.store.income_opportunities(500, client_id=client_id)
        counts = {s: 0 for s in self.ORDER}
        for row in rows:
            s = str(row.get("status") or "DISCOVERY")
            counts[s] = counts.get(s, 0) + 1
        return {
            "counts": counts,
            "external_execution_ready": False,
            "reason": "يمكن إنشاء طلب دفع بعد التسليم؛ الاعتراف بالإيراد يتطلب مصالحة مستقلة للدفع.",
            "payment_verified_jod": sum(float(x.get("verified_amount_jod") or 0) for x in rows if x.get("revenue_realized")),
            "client_id": client_id,
        }
