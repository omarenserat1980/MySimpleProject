"""Freelance opportunity and income operations for BrainV12.

This module prepares and scores freelance opportunities, generates a proposal
from approved templates, and tracks the evidence needed for verified revenue.
It deliberately does not submit offers, impersonate users, move money, or
treat an opportunity as income.
"""
from __future__ import annotations

from time import time
from typing import Any


PROFILE = {
    "brand": "BrainV12",
    "headline": "تطوير مواقع وأنظمة وأتمتة وحلول C#/.NET وPython",
    "skills": [
        "C#", ".NET", "Python", "FastAPI", "REST API", "Web Development",
        "Automation", "WhatsApp integration", "E-commerce", "Product Listing",
        "Arabic Content", "Data Entry", "SEO", "Short Video",
    ],
    "services": [
        "تطوير وتعديل مواقع الويب",
        "ربط API وWhatsApp والخدمات الخارجية",
        "تطوير C#/.NET وPython",
        "تهيئة المتاجر وإضافة المنتجات",
        "أتمتة المهام الإدارية",
        "كتابة أوصاف المنتجات والمحتوى العربي",
    ],
    "portfolio": [
        {
            "title": "Electronic Brain V12",
            "description": "منصة برمجية متعددة الأنظمة للتفكير والذاكرة والمهام والصلاحيات والأتمتة.",
            "status": "IN_DEVELOPMENT",
        },
        {
            "title": "Arabic E-commerce Workflow",
            "description": "تصور عملي لمتجر عربي لإدارة المنتجات والوصف والأسعار والنشر.",
            "status": "IN_DEVELOPMENT",
        },
    ],
}


PROPOSAL_TEMPLATES = {
    "web": """السلام عليكم،
اطلعت على تفاصيل المشروع ويمكنني المساعدة في تنفيذ المطلوب ضمن نطاق واضح.
سأبدأ بفحص التقنية الحالية وتحديد نقاط التعديل، ثم أنفذ التغييرات المطلوبة وأختبرها على الويب والهاتف قبل التسليم.
إذا أرسلتم تفاصيل الموقع والتقنيات المستخدمة، أستطيع تحديد خطوات التنفيذ والمدة بدقة.
تحياتي، BrainV12""",
    "ecommerce": """السلام عليكم،
اطلعت على المشروع، ويمكنني تنفيذ إعداد المتجر وتنظيم المنتجات والأسعار والوصف والبيانات المطلوبة.
سأعمل على ترتيب البيانات واختبار ظهور المنتجات والطلبات قبل التسليم، مع الالتزام بنطاق العمل المتفق عليه.
أرسلوا تفاصيل المنصة وعدد المنتجات والمخرجات المطلوبة لنحدد خطة التنفيذ بدقة.
تحياتي، BrainV12""",
    "automation": """السلام عليكم،
يمكنني تنفيذ أتمتة المهمة المطلوبة وربط الأنظمة أو الخدمات اللازمة عبر API عند توفرها.
سأقسم العمل إلى خطوات قابلة للاختبار، وأتحقق من الحالات الأساسية والأخطاء قبل التسليم.
أحتاج تفاصيل الأدوات الحالية ونطاق الأتمتة المطلوب لتحديد الحل المناسب.
تحياتي، BrainV12""",
    "data": """السلام عليكم،
يمكنني تنفيذ إدخال وتنظيم البيانات المطلوبة مع مراجعة العينات والتأكد من اتساق الحقول والأسعار والوصف.
سأعمل وفق نموذج واضح للتسليم حتى يمكن مراجعة النتيجة بسهولة.
أرسلوا عينة من البيانات وعدد السجلات والمنصة المستخدمة لتحديد حجم العمل بدقة.
تحياتي، BrainV12""",
    "general": """السلام عليكم،
اطلعت على متطلبات المشروع ويمكنني المساعدة في تنفيذه ضمن نطاق واضح وقابل للاختبار.
قبل البدء سأراجع المتطلبات والتقنيات والمخرجات المطلوبة، ثم أقسم العمل إلى خطوات وأختبر النتيجة قبل التسليم.
أرسلوا التفاصيل أو رابط المشروع لأحدد خطة التنفيذ المناسبة.
تحياتي، BrainV12""",
}


KEYWORDS = {
    "web": {"website", "web", "موقع", "مواقع", "صفحة", "landing", "asp.net", ".net"},
    "ecommerce": {"store", "shop", "ecommerce", "متجر", "منتجات", "products", "زد", "سلة"},
    "automation": {"automation", "api", "whatsapp", "أتمتة", "واتساب", "ربط", "integration"},
    "data": {"data entry", "إدخال", "بيانات", "excel", "products", "منتجات", "تنظيم"},
}


class FreelanceAgent:
    """Analysis-first freelance agent with human-controlled external actions."""

    def __init__(self, store):
        self.store = store
        self.profile = PROFILE
        self.runs = 0

    def profile_snapshot(self) -> dict[str, Any]:
        return {
            "ok": True,
            "profile": self.profile,
            "external_actions": {
                "account_creation": "HUMAN_CONTROLLED",
                "offer_submission": "HUMAN_CONTROLLED",
                "client_messages": "HUMAN_CONTROLLED",
                "payment_movement": "HUMAN_CONTROLLED",
            },
        }

    def _text(self, opportunity: dict[str, Any]) -> str:
        return " ".join(str(opportunity.get(k, "")) for k in ("title", "requirements", "description", "category")).lower()

    def analyze(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        text = self._text(opportunity)
        quality_ok = bool(str(opportunity.get("source_url") or opportunity.get("url") or "").strip()) and bool(str(opportunity.get("evidence") or "").strip()) and len(str(opportunity.get("title") or "").strip()) >= 8)
        matched = []
        categories = []
        for category, words in KEYWORDS.items():
            hits = [w for w in words if w.lower() in text]
            if hits:
                categories.append(category)
                matched.extend(hits)
        skill_hits = [s for s in self.profile["skills"] if s.lower() in text]
        score = min(100, 25 + len(set(matched)) * 7 + len(skill_hits) * 8)
        if any(x in text for x in ("senior", "خبرة 5 سنوات", "5+ years")):
            score -= 15
        if any(x in text for x in ("urgent", "عاجل", "today", "اليوم")):
            score -= 5
        score = max(0, score)
        if not quality_ok:
            score = min(score, 40)
        return {
            "ok": True,
            "fit_score": score,
            "quality_ok": quality_ok,
            "categories": categories or ["general"],
            "matched_terms": sorted(set(matched)),
            "matched_skills": skill_hits,
            "recommendation": "PREPARE_OFFER" if score >= 55 and quality_ok else "REVIEW_MANUALLY",
            "reason": "تقييم ملاءمة فني فقط؛ ليس توقعًا للقبول أو الربح.",
        }

    def prepare_offer(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        analysis = self.analyze(opportunity)
        category = analysis["categories"][0]
        template = PROPOSAL_TEMPLATES.get(category, PROPOSAL_TEMPLATES["general"])
        self.store.event("FREELANCE_OFFER_PREPARED", {
            "title": str(opportunity.get("title", ""))[:200],
            "fit_score": analysis["fit_score"],
            "external_submission": False,
        })
        return {
            "ok": True,
            "opportunity": opportunity,
            "analysis": analysis,
            "proposal": template,
            "submission_status": "NOT_SUBMITTED",
            "next_action": "HUMAN_REVIEW_AND_SUBMIT",
        }

    def record_application(self, opportunity_id: str, status: str, evidence: str = "") -> dict[str, Any]:
        allowed = {"PREPARED", "SUBMITTED", "CLIENT_RESPONDED", "ACCEPTED", "DELIVERING", "COMPLETED", "PAYMENT_PENDING"}
        if status not in allowed:
            return {"ok": False, "status": "INVALID_STATUS"}
        if status in {"SUBMITTED", "CLIENT_RESPONDED", "ACCEPTED", "DELIVERING", "COMPLETED", "PAYMENT_PENDING"} and not evidence.strip():
            return {"ok": False, "status": "EVIDENCE_REQUIRED"}
        self.store.event("FREELANCE_APPLICATION_STATUS", {
            "opportunity_id": opportunity_id, "status": status,
            "evidence": evidence[:2000], "timestamp": time(),
        })
        return {"ok": True, "opportunity_id": opportunity_id, "status": status, "recorded": True}

    def record_verified_payment(self, opportunity_id: str, amount_jod: float, evidence: str) -> dict[str, Any]:
        amount = float(amount_jod)
        if amount <= 0 or not evidence.strip():
            return {"ok": False, "status": "PAYMENT_EVIDENCE_REQUIRED"}
        result = self.store.income_summary()
        self.store.event("FREELANCE_PAYMENT_VERIFIED", {
            "opportunity_id": opportunity_id,
            "amount_jod": amount,
            "evidence": evidence[:2000],
            "previous_verified_total_jod": float(result.get("verified", 0) or 0),
        })
        return {
            "ok": True,
            "status": "VERIFIED",
            "opportunity_id": opportunity_id,
            "amount_jod": amount,
            "note": "تم تسجيل دليل الدفع؛ يجب أن يبقى المصدر قابلًا للمراجعة.",
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "ok": True,
            "brand": "BrainV12",
            "profile_ready": True,
            "proposal_templates": sorted(PROPOSAL_TEMPLATES),
            "verified_revenue_jod": float(self.store.income_summary().get("verified", 0) or 0),
            "external_submission": "HUMAN_CONTROLLED",
            "payment_movement": "HUMAN_CONTROLLED",
            "runs": self.runs,
        }
