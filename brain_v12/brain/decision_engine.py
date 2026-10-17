from dataclasses import dataclass, asdict
import os
from pathlib import Path

from .bitcoin_north_star import BitcoinNorthStar
from .run_evidence_store import RunEvidenceStore
from .engineering_factory import EngineeringFactory


@dataclass
class Candidate:
    id: str
    action: str
    expected: str
    risk: str = "low"
    requirements: list[str] | None = None
    reversible: bool = True
    evidence: list[str] | None = None
    confidence: float = .5
    tool_id: str | None = None

    def __post_init__(self):
        self.requirements = self.requirements or []
        self.evidence = self.evidence or []


class DecisionEngine:
    """Decision selection guarded by the persistent Bitcoin mission policy."""

    NORTH_STAR_COMMANDS = {"n", "north star", "bitcoin north star"}
    NORTH_STAR_GOAL = (
        "Bitcoin mining mission: inspect current evidence and CI, identify the nearest verified blocker, "
        "prioritize real SHA-256/Stratum mining and accepted-share proof, then payout and net-profit "
        "reconciliation; choose the smallest safe next step and never treat simulation as revenue."
    )

    @classmethod
    def normalize_goal(cls, goal):
        raw = str(goal or "").strip()
        if raw.casefold() in cls.NORTH_STAR_COMMANDS:
            return cls.NORTH_STAR_GOAL
        return raw

    def __init__(self, north_star: BitcoinNorthStar | None = None):
        self.history = []
        self.engineering_factory = EngineeringFactory()
        if north_star is None:
            evidence_path = Path(os.environ.get(
                "BRAIN_NORTH_STAR_EVIDENCE_PATH",
                str(Path.home() / ".brain_v12" / "bitcoin_north_star.jsonl"),
            ))
            north_star = BitcoinNorthStar(evidence_store=RunEvidenceStore(evidence_path))
        self.north_star = north_star

    @staticmethod
    def _is_income_goal(goal: str) -> bool:
        text = str(goal or "").casefold()
        terms = (
            "income", "earn", "earning", "revenue", "profit", "paid work",
            "freelance", "client", "sales", "monetize", "money", "دخل",
            "كسب", "كسب المال", "إيراد", "ربح", "مصاري", "فرصة مدفوعة",
            "عميل", "بيع", "تحقيق الدخل",
        )
        return any(term in text for term in terms)

    @staticmethod
    def _mission_tags(goal: str) -> list[str]:
        text = (goal or "").lower()
        tags = []
        bitcoin_context = any(term in text for term in ("bitcoin", "بيتكوين", "btc", "mining", "التعدين", "stratum", "asic", "pool", "sha-256", "sha256"))
        if not bitcoin_context:
            return []
        if any(term in text for term in ("bitcoin", "بيتكوين", "btc", "mining", "التعدين", "stratum", "asic", "pool", "sha-256", "sha256")):
            tags.append("REAL_BTC_MINING")
        if any(term in text for term in ("profit", "ربح", "revenue", "إيراد", "payout", "ربحية", "economic", "اقتصاد")):
            tags.append("VERIFIED_NET_PROFIT")
        if any(term in text for term in ("worker", "عامل", "software", "برمج", "كود", "code", "sha-256", "sha256", "stratum", "asic")):
            tags.append("BITCOIN_MINING_SOFTWARE")
        if any(term in text for term in ("test", "اختبار", "verify", "تحقق", "security", "أمن", "runner", "executor", "evidence", "دليل", "memory", "ذاكرة")):
            tags.extend(["CI_VERIFICATION", "SECURITY"])
        return tags

    def generate(self, goal):
        goal = self.normalize_goal(goal)
        text = (goal or "").lower()
        code = any(x in text for x in ("كود", "برمج", "ملف", "github", "code", "تطوير", "إصلاح"))
        device = any(x in text for x in ("termux", "redmi", "هاتف", "جهاز", "موبايل", "جوال", "android", "device", "agent", "عامل"))
        memory = any(x in text for x in ("ذاكرة", "تذكر", "memory", "سجل"))
        options = [
            asdict(Candidate("engineering_proposal", "إنشاء اقتراح هندسي قابل للاختبار", "خطة مرتبطة بالأدلة والاختبارات والتكامل", "low", [], True, ["goal"], .99, "engineering.propose")),
            asdict(Candidate("observe", "قراءة وفهم الحالة", "بيانات قابلة للتحقق", "low", [], True, ["goal"], .82,
                             "memory.read" if memory else "state.read")),
            asdict(Candidate("plan", "بناء خطة متعددة الخطوات", "خطة قابلة للتحقق", "low", [], True, ["goal"], .80, "tasks.create")),
        ]
        if self._is_income_goal(goal):
            options.insert(0, asdict(Candidate(
                "income_opportunities",
                "البحث عن فرص دخل حقيقية قابلة للتنفيذ بأقل تكلفة",
                "فرص موثقة مع متطلبات وسعر/ميزانية وتكلفة التنفيذ والخطوة التالية",
                "low", [], True, ["goal", "opportunity_evidence"], .99, "income.search",
            )))
        if device:
            options.insert(0, asdict(Candidate("device", "تنفيذ مهمة آمنة على الجهاز", "نتيجة موثقة من Termux", "medium", ["device_agent"], True, ["goal", "device_result"], .92, "device.enqueue")))
        if code:
            options.insert(0, asdict(Candidate("inspect_code", "فحص الكود المستهدف", "صورة فعلية عن الكود الحالي", "low", [], True, ["goal", "code"], .88, "code.inspect")))
            options.append(asdict(Candidate("verify_code", "التحقق من الكود", "نتيجة اختبار/تحقق موثقة", "low", [], True, ["code"], .84, "code.verify")))
            options.append(asdict(Candidate("apply_code", "تطبيق تحسين برمجي", "تغيير قابل للتراجع مع تحقق", "high", ["developer_approval"], True, ["code", "approval"], .65, "code.apply")))
        options.append(asdict(Candidate("act", "تنفيذ خطوة حساسة", "نتيجة خارجية قابلة للتحقق", "high", ["agent_approval"], True, ["goal", "approval"], .55, "agent.execute")))
        return options

    def choose(self, goal, options, permissions=None):
        permissions = permissions or set()
        original_goal = goal
        goal = self.normalize_goal(goal)
        bitcoin_tags = self._mission_tags(str(goal))
        income_goal = self._is_income_goal(str(goal)) and not bitcoin_tags
        compass = None
        # Bitcoin's North Star governs Bitcoin tasks. It must not accidentally
        # veto legitimate non-Bitcoin income paths such as freelance services.
        # General non-income tasks retain the previous mission-alignment gate.
        if not income_goal:
            compass = self.north_star.assess({
                "task_id": "decision-" + str(len(self.history) + 1),
                "tags": bitcoin_tags,
                "expected_progress": 0.5,
                "evidence_status": "MISSING",
            })
            if compass.status == "OFF_COURSE":
                result = {
                    "status": "MISSION_ALIGNMENT_REQUIRED",
                    "goal": original_goal,
                    "selected": None,
                    "reason": "bitcoin_north_star",
                    "north_star": compass.as_dict(),
                    "next_action": compass.next_action,
                    "alternatives": [],
                }
                self.history.append(result)
                return result

        compass_data = compass.as_dict() if compass is not None else {
            "status": "NOT_APPLICABLE",
            "reason": "NON_BITCOIN_INCOME_OBJECTIVE",
        }
        ranked = []
        for option in options:
            required = option.get("requirements", [])
            missing = [item for item in required if item not in permissions]
            blocked = bool(missing)
            score = float(option.get("confidence", .5))
            if income_goal:
                searchable = " ".join(str(option.get(key, "")) for key in ("id", "action", "expected", "tool_id")).casefold()
                income_markers = ("income", "earn", "revenue", "profit", "opportunit", "freelance", "client", "payment", "دخل", "ربح", "إيراد", "فرص")
                if any(marker in searchable for marker in income_markers):
                    score += 0.20
            if option.get("risk") == "high":
                score -= .30
            if not option.get("reversible", True):
                score -= .15
            if blocked:
                score -= .50
            ranked.append((score, option, blocked, missing))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            result = {"status": "NO_OPTIONS", "goal": original_goal, "north_star": compass_data}
        else:
            score, selected, blocked, missing = ranked[0]
            if blocked and selected.get("risk") == "high":
                result = {"status": "WAITING_APPROVAL", "goal": original_goal, "normalized_goal": goal, "selected": selected,
                          "score": round(score, 3), "reason": "required_permission",
                          "missing_permissions": missing, "alternatives": [item[1] for item in ranked[1:]],
                          "north_star": compass_data}
            else:
                result = {"status": "DECIDED", "goal": original_goal, "normalized_goal": goal, "selected": selected,
                          "score": round(score, 3), "reason": "tool_aware_heuristic",
                          "alternatives": [item[1] for item in ranked[1:]], "north_star": compass_data}
        self.history.append(result)
        return result
