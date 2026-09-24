"""External Work Gateway V1.

A permission-gated bridge between the internal workforce and external work
platforms. It can register user-owned accounts, ingest opportunities supplied
by an approved connector, score/route work, draft proposals, track orders and
record only verified payouts.

It deliberately does not store passwords/2FA secrets, bypass platform rules,
send unsolicited spam, sign contracts, or move money.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from time import time
from typing import Any, Iterable
from .platform_adapters import PlatformAdapterRegistry
from .work_queue import ExternalWorkQueue
from .compliance_gate import ComplianceGate
from .external_work_metrics import summarize as summarize_metrics


class Platform(str, Enum):
    UPWORK = "UPWORK"
    FIVERR = "FIVERR"
    FREELANCER = "FREELANCER"
    MOSTAQL = "MOSTAQL"
    KHAMSAT = "KHAMSAT"
    LINKEDIN = "LINKEDIN"


class WorkStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    DRAFTED = "DRAFTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    ORDERED = "ORDERED"
    IN_PRODUCTION = "IN_PRODUCTION"
    QA = "QA"
    DELIVERED = "DELIVERED"
    PAID = "PAID"
    REJECTED = "REJECTED"


@dataclass
class PlatformAccount:
    platform: str
    account_label: str
    owner_controlled: bool = True
    identity_verified: bool = False
    connector_enabled: bool = False
    permission_scope: str = "READ_AND_DRAFT"
    status: str = "PENDING"


@dataclass
class Opportunity:
    opportunity_id: str
    platform: str
    title: str
    description: str
    skills: tuple[str, ...]
    budget_jod: float | None = None
    stage: str = WorkStage.DISCOVERED.value
    assigned_employee_id: str | None = None
    source_url: str | None = None


@dataclass
class WorkOrder:
    order_id: str
    opportunity_id: str
    platform: str
    employee_id: str | None
    agreed_amount_jod: float
    stage: str = WorkStage.ORDERED.value
    payment_verified: bool = False
    evidence: str | None = None


class ExternalWorkGateway:
    """Safe control plane for external work.

    Connectors are adapters, not credentials vaults. A connector may supply
    public/authorized opportunity data and submit an action only when the
    platform and account permission explicitly allow it.
    """

    ALLOWED_PLATFORMS = {p.value for p in Platform}
    SAFE_SCOPES = {"READ_ONLY", "READ_AND_DRAFT"}
    USER_APPROVAL_REQUIRED = {
        "SUBMIT_PROPOSAL", "ACCEPT_OFFER", "SIGN_CONTRACT",
        "PUBLISH_ACCOUNT_CHANGES", "WITHDRAW_FUNDS", "TRANSFER_FUNDS",
    }

    def __init__(self, organization: Any) -> None:
        self.organization = organization
        self.accounts: dict[str, PlatformAccount] = {}
        self.opportunities: dict[str, Opportunity] = {}
        self.orders: dict[str, WorkOrder] = {}
        self.audit_log: list[dict[str, Any]] = []
        self._opportunity_counter = 0
        self._order_counter = 0
        self.adapters = PlatformAdapterRegistry()
        self.queue = ExternalWorkQueue()
        self.compliance = ComplianceGate()

    def _audit(self, event: str, **data: Any) -> None:
        self.audit_log.append({"timestamp": time(), "event": event, **data})

    def register_account(
        self, platform: str, account_label: str, *,
        identity_verified: bool = False,
        connector_enabled: bool = False,
        permission_scope: str = "READ_AND_DRAFT",
    ) -> dict[str, Any]:
        platform = platform.upper()
        if platform not in self.ALLOWED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        if permission_scope not in self.SAFE_SCOPES:
            raise ValueError("Use READ_ONLY or READ_AND_DRAFT; stronger actions require explicit approval.")
        account = PlatformAccount(
            platform=platform,
            account_label=account_label,
            identity_verified=identity_verified,
            connector_enabled=connector_enabled,
            permission_scope=permission_scope,
            status="ACTIVE" if identity_verified else "PENDING_VERIFICATION",
        )
        self.accounts[f"{platform}:{account_label}"] = account
        self._audit("ACCOUNT_REGISTERED", platform=platform, account_label=account_label)
        return asdict(account)

    def ingest_opportunity(
        self, platform: str, title: str, description: str,
        skills: Iterable[str], budget_jod: float | None = None,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        platform = platform.upper()
        if platform not in self.ALLOWED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        self._opportunity_counter += 1
        item = Opportunity(
            opportunity_id=f"OPP-{self._opportunity_counter:06d}",
            platform=platform,
            title=title,
            description=description,
            skills=tuple(skills),
            budget_jod=budget_jod,
            source_url=source_url,
        )
        self.opportunities[item.opportunity_id] = item
        self._audit("OPPORTUNITY_INGESTED", opportunity_id=item.opportunity_id, platform=platform)
        self.queue.enqueue(item.opportunity_id, priority=0.5)
        return asdict(item)

    def _skill_score(self, employee: Any, opportunity: Opportunity) -> float:
        employee_skills = {str(x).lower() for x in getattr(employee, "skills", [])}
        wanted = {str(x).lower() for x in opportunity.skills}
        if not wanted:
            return 0.5
        return len(employee_skills & wanted) / len(wanted)

    def route_opportunity(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self.opportunities[opportunity_id]
        candidates = [
            e for e in self.organization.employees.values()
            if getattr(e, "status", "ACTIVE") in {"ACTIVE", "AVAILABLE", "BUSY", "TRAINING_REQUIRED"}
        ]
        if not candidates:
            raise RuntimeError("No active employees available.")
        ranked = sorted(
            candidates,
            key=lambda e: (
                self._skill_score(e, opportunity),
                -getattr(e, "completed_tasks", 0),
                getattr(e, "employee_id", ""),
            ),
            reverse=True,
        )
        chosen = ranked[0]
        opportunity.assigned_employee_id = chosen.employee_id
        opportunity.stage = WorkStage.QUALIFIED.value
        self._audit("OPPORTUNITY_ROUTED", opportunity_id=opportunity_id, employee_id=chosen.employee_id)
        return {"opportunity": asdict(opportunity), "employee_id": chosen.employee_id}

    def draft_proposal(self, opportunity_id: str) -> dict[str, Any]:
        opportunity = self.opportunities[opportunity_id]
        if opportunity.assigned_employee_id is None:
            self.route_opportunity(opportunity_id)
        amount = opportunity.budget_jod or 0.0
        proposal = {
            "opportunity_id": opportunity_id,
            "platform": opportunity.platform,
            "employee_id": opportunity.assigned_employee_id,
            "draft": (
                f"مرحباً، اطلعنا على طلبكم: {opportunity.title}. "
                "يمكننا تنفيذ العمل وفق المتطلبات المتاحة مع تسليم منظم ومراجعة جودة قبل التسليم."
            ),
            "proposed_amount_jod": round(float(amount), 2),
            "requires_user_approval": True,
            "stage": WorkStage.AWAITING_APPROVAL.value,
        }
        opportunity.stage = WorkStage.DRAFTED.value
        self._audit("PROPOSAL_DRAFTED", opportunity_id=opportunity_id)
        return proposal

    def record_order(
        self, opportunity_id: str, agreed_amount_jod: float,
        *,
        employee_id: str | None = None,
    ) -> dict[str, Any]:
        opportunity = self.opportunities[opportunity_id]
        if agreed_amount_jod < 0:
            raise ValueError("Amount cannot be negative.")
        self._order_counter += 1
        order = WorkOrder(
            order_id=f"ORD-{self._order_counter:06d}",
            opportunity_id=opportunity_id,
            platform=opportunity.platform,
            employee_id=employee_id or opportunity.assigned_employee_id,
            agreed_amount_jod=float(agreed_amount_jod),
        )
        self.orders[order.order_id] = order
        opportunity.stage = WorkStage.ORDERED.value
        self._audit("ORDER_RECORDED", order_id=order.order_id)
        return asdict(order)

    def verify_payment(
        self, order_id: str, received_amount_jod: float, evidence: str,
    ) -> dict[str, Any]:
        order = self.orders[order_id]
        received = float(received_amount_jod)
        if received < 0:
            raise ValueError("Received amount cannot be negative.")
        if not evidence.strip():
            raise ValueError("Payment evidence is required.")
        if received < order.agreed_amount_jod:
            raise ValueError("Received amount is below the agreed order amount.")
        order.payment_verified = True
        order.stage = WorkStage.PAID.value
        order.evidence = evidence
        self._audit("PAYMENT_VERIFIED", order_id=order_id, amount_jod=received)
        return asdict(order)

    def verified_revenue_jod(self) -> float:
        return round(sum(o.agreed_amount_jod for o in self.orders.values() if o.payment_verified), 2)

    def evaluate_action(self, action: str, *, authorized: bool = False) -> dict[str, Any]:
        return asdict(self.compliance.evaluate(action, authorized=authorized))

    def metrics(self) -> dict[str, Any]:
        return summarize_metrics(self.opportunities, self.orders, self.accounts)

    def snapshot(self) -> dict[str, Any]:
        return {
            "accounts": [asdict(x) for x in self.accounts.values()],
            "opportunities": [asdict(x) for x in self.opportunities.values()],
            "orders": [asdict(x) for x in self.orders.values()],
            "verified_revenue_jod": self.verified_revenue_jod(),
            "audit_events": len(self.audit_log),
            "external_money_movement": False,
            "credentials_stored": False,
            "user_approval_required_for_submission": True,
            "adapter_capabilities": self.adapters.capabilities(),
            "queue": self.queue.snapshot(),
            "metrics": self.metrics(),
        }
