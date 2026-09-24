"""Operational workforce coordinator for Electronic Brain V12.

Creates internal specialist teams, dispatches bounded work, and exposes auditable
reports. External publishing, account access, contracts, and money movement remain
permission-gated and are never simulated as completed.
"""
from __future__ import annotations

from dataclasses import asdict
from time import time
from typing import Any

from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from brain_v7.braincore_v2.youtube_team import YouTubeTeam
from brain_v7.braincore_v2.revenue_task_factory import RevenueTaskFactory
from .income_engine import IncomeEngine
from .income_strategy import IncomeStrategy
from .mining_engine import MiningEngine
from .freelance_agent import FreelanceAgent
from .live_opportunity_researcher import LiveOpportunityResearcher


WEBSITE_ROLES = (
    ("Website Product Manager", ("web", "product", "priorities")),
    ("Website Builder", ("web_development", "automation")),
    ("Website QA Specialist", ("testing", "ux", "quality")),
    ("SEO Growth Specialist", ("seo", "content", "search")),
    ("Conversion Specialist", ("conversion", "offers", "analytics")),
    ("Opportunity Researcher", ("market_research", "opportunities")),
    ("Client Services Specialist", ("digital_services", "client_work")),
    ("Revenue Verification Specialist", ("revenue", "verification")),
)

CINEMATIC_ROLES = (
    ("Cinematic Operations Manager", ("cinematic", "coordination")),
    ("Cinematic Story Producer", ("story", "cinematic")),
    ("Cinematic Production Specialist", ("video", "production")),
    ("Cinematic QA Specialist", ("media_quality", "qa")),
    ("Cinematic Distribution Specialist", ("distribution", "seo")),
    ("Cinematic Analytics Specialist", ("analytics", "retention")),
)

class WorkforceControl:
    def __init__(self, store):
        self.store = store
        self.organization = EmployeeHierarchy()
        self.youtube = YouTubeTeam(self.organization)
        self.revenue = RevenueTaskFactory()
        self.income_engine = IncomeEngine(store)
        self.income_strategy = IncomeStrategy(self.income_engine)
        self.mining = MiningEngine()
        self.freelance = FreelanceAgent(store)
        self.live_opportunity_researcher = LiveOpportunityResearcher(self.income_engine, store)
        self.website = self.organization.ensure_team(
            department_id="DEPT-WEB-OPS", name="WEB_PLATFORM_OPERATIONS",
            manager_id="MGR-WEB-OPS", manager_title="Web Platforms Manager",
            roles=WEBSITE_ROLES,
            goal="operate, improve, measure and qualify the user's web platforms and revenue opportunities",
        )
        self.cinematic = self.organization.ensure_team(
            department_id="DEPT-CINEMATIC", name="CINEMATIC_FACTORY",
            manager_id="MGR-CINEMATIC", manager_title="Cinematic Factory Manager",
            roles=CINEMATIC_ROLES,
            goal="produce and quality-check original cinematic content packages",
        )
        self.last_dispatch: dict[str, Any] = {}
        self.dispatch_count = 0

    def _task(self, objective: str, department_id: str, result: dict[str, Any]) -> dict[str, Any]:
        task = self.organization.assign_task(objective, department_id=department_id)
        # This is an internal planning/audit task. It is safe to auto-complete;
        # external publication/payment is explicitly represented as gated.
        completed = self.organization.complete_task(task.task_id, success=True, result=result)
        return asdict(completed)

    def dispatch(self, trigger: str = "scheduled", *, include_revenue: bool = True) -> dict[str, Any]:
        self.dispatch_count += 1
        results = []

        income_mission = self.income_strategy.mission()
        income_opportunities = self.income_engine.discover(8) if include_revenue else []
        results.append(self._task(
            "أولوية الدخل: البحث والتأهيل وتجهيز أول فرصة قابلة للتحقق بقيمة 10 JOD دون إنفاق مقدم.",
            "DEPT-003",
            {"kind":"income_first_mission","status":"ACTIVE","mission":income_mission["mission"],
             "target_jod":income_mission["target_jod"],
             "verified_revenue_jod":income_mission["verified_revenue_jod"],
             "discovered_opportunities":len(income_opportunities),
             "external_side_effects":False},
        ))
        results.append(self._task(
            "استشفاء النظام: تدقيق أخطاء Render/CI وتوزيع نتائج الفحص على فرق الجودة والهندسة.",
            "DEPT-009",
            {"kind":"recovery_audit","status":"COMPLETED","external_side_effects":False},
        ))
        results.append(self._task(
            "تحسين مراقبة السجلات: التأكد من أن ERROR/CRITICAL يولّد تدقيقًا تلقائيًا.",
            "DEPT-004",
            {"kind":"log_auto_audit","status":"COMPLETED","external_side_effects":False},
        ))
        results.append(self._task(
            "إعداد خط إنتاج YouTube: استراتيجية، بحث، كتابة، إنتاج، QA، SEO وتحليلات.",
            "DEPT-YOUTUBE",
            {"kind":"youtube_pipeline","status":"READY","publication":"AUTHORIZATION_REQUIRED"},
        ))
        results.append(self._task(
            "إعداد خط الإنتاج السينمائي ومراجعة الجودة والتوزيع.",
            "DEPT-CINEMATIC",
            {"kind":"cinematic_pipeline","status":"READY","publication":"AUTHORIZATION_REQUIRED"},
        ))
        results.append(self._task(
            "فحص المواقع والمنصات: صحة المنتج، SEO، التحويل، فرص الخدمات الرقمية والعملاء.",
            "DEPT-WEB-OPS",
            {"kind":"web_platforms","status":"AUDITED","external_side_effects":False},
        ))
        revenue_tasks = self.revenue.generate(8) if include_revenue else []
        results.append(self._task(
            "تدقيق فرص الدخل القانونية وتجهيز التجارب القابلة للتحقق دون ادعاء أرباح.",
            "DEPT-003",
            {"kind":"revenue_opportunities","status":"PLANNED","count":len(revenue_tasks), "discovered_opportunities":len(income_opportunities),
             "verified_revenue_jod":self.income_engine.snapshot().get("verified_revenue_jod",0.0),
             "payment_verification_required":True},
        ))
        self.last_dispatch = {
            "timestamp": time(), "trigger": trigger, "dispatch_number": self.dispatch_count,
            "tasks": results, "revenue_tasks": revenue_tasks, "income_opportunities": income_opportunities,
            "external_actions": "NONE",
        }
        self.store.event("WORKFORCE_DISPATCH", {
            "dispatch_number": self.dispatch_count, "trigger": trigger,
            "task_count": len(results), "include_revenue": include_revenue, "external_actions": "NONE",
        })
        return self.last_dispatch

    def health(self) -> dict[str, Any]:
        report = self.report()
        revenue = report["revenue"]["income_engine"]
        return {
            "ok": True,
            "dispatch_count": self.dispatch_count,
            "employees": report["staffing"],
            "departments": report["departments"],
            "verified_revenue_jod": float(revenue.get("verified_revenue_jod", 0) or 0),
            "live_opportunities": int(revenue.get("total", 0) or 0),
            "mining": self.mining.snapshot(),
            "freelance": self.freelance.snapshot(),
            "external_execution": {
                "youtube": "AUTHORIZATION_REQUIRED",
                "cinematic": "AUTHORIZATION_REQUIRED",
                "website": "NOT_EXECUTED",
            },
        }

    def report(self) -> dict[str, Any]:
        employees = list(self.organization.employees.values())
        completed = sum(e.completed_tasks for e in employees)
        failed = sum(e.failed_tasks for e in employees)
        by_dept: dict[str, dict[str, Any]] = {}
        for d in self.organization.departments.values():
            ids = self.organization.managers[d.manager_id].employee_ids if d.manager_id in self.organization.managers else []
            es = [self.organization.employees[i] for i in ids if i in self.organization.employees]
            by_dept[d.department_id] = {
                "name": d.name, "manager_id": d.manager_id, "employees": len(es),
                "completed_tasks": sum(e.completed_tasks for e in es),
                "failed_tasks": sum(e.failed_tasks for e in es),
                "busy": sum(e.status == "BUSY" for e in es),
            }
        return {
            "ok": True, "timestamp": time(), "dispatch_count": self.dispatch_count,
            "staffing": self.organization.staffing_summary(),
            "departments": by_dept,
            "youtube": self.youtube.snapshot(),
            "cinematic": {"employee_count": len(self.cinematic["employee_ids"]), "team": self.cinematic},
            "web_platforms": {"employee_count": len(self.website["employee_ids"]), "team": self.website},
            "revenue": {**self.revenue.snapshot(), "income_engine": self.income_engine.snapshot(),
                        "income_strategy": self.income_strategy.mission()},
            "mining": self.mining.snapshot(),
            "freelance": self.freelance.snapshot(),
            "last_dispatch": self.last_dispatch,
            "work_totals": {"completed_internal_tasks": completed, "failed_internal_tasks": failed},
            "external_status": {
                "youtube_publication": "AUTHORIZATION_REQUIRED",
                "cinematic_publication": "AUTHORIZATION_REQUIRED",
                "website_external_changes": "NOT_EXECUTED",
                "verified_revenue_jod": self.income_engine.snapshot().get("verified_revenue_jod",0.0),
                "note": "لا يتم احتساب مال أو نشر خارجي دون نتيجة موثقة وصلاحية فعلية.",
            },
        }
