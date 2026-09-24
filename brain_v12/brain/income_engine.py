"""Verified-income engine for Electronic Brain V12.

The engine separates opportunity discovery from revenue recognition. It creates
auditable, low-cost experiments, records evidence, and never counts expected
money as received money.
"""
from __future__ import annotations

from time import time
from typing import Any
import hashlib


class IncomeEngine:
    CHANNELS = (
        {
            "category": "DIGITAL_SERVICES",
            "title": "خدمات مواقع وأتمتة للشركات الصغيرة",
            "source_url": "https://www.upwork.com/nx/search/jobs/",
            "evidence": "منصة عمل حر تعرض وظائف؛ وجود الوظيفة أو إرسال عرض لا يعني قبولًا أو دفعًا.",
            "owner_role": "Client Services Specialist",
            "action": "ابحث عن طلبات حديثة مناسبة لخدمات المواقع والأتمتة، ثم سجّل فقط الطلبات القابلة للتقديم.",
            "cost": 0,
        },
        {
            "category": "DIGITAL_SERVICES",
            "title": "خدمات رقمية عربية عبر خمسات",
            "source_url": "https://khamsat.com/",
            "evidence": "منصة خدمات مصغرة؛ إنشاء خدمة لا يساوي بيعًا أو إيرادًا.",
            "owner_role": "Client Services Specialist",
            "action": "دراسة الطلب على خدمات عربية صغيرة يمكن تنفيذها وتسليمها بسرعة.",
            "cost": 0,
        },
        {
            "category": "DIGITAL_SERVICES",
            "title": "خدمات عربية مستقلة عبر مستقل",
            "source_url": "https://mostaql.com/",
            "evidence": "منصة مشاريع عربية؛ التقديم لا يساوي عقدًا أو دفعًا.",
            "owner_role": "Opportunity Researcher",
            "action": "العثور على مشاريع حديثة مناسبة ثم تقييم المتطلبات قبل التقديم.",
            "cost": 0,
        },
        {
            "category": "LOCAL_SERVICES",
            "title": "بيع خدمة رقمية مباشرة لأعمال محلية",
            "source_url": "https://www.google.com/maps",
            "evidence": "يمكن العثور على أعمال محلية علنية واحتياجات رقمية محتملة؛ لا يوجد دخل قبل قبول العميل والدفع.",
            "owner_role": "Client Services Specialist",
            "action": "بناء قائمة عملاء محتملين من مصادر علنية، ثم تجهيز عرض خدمة واضح دون مراسلة أو تعاقد تلقائي غير مصرح.",
            "cost": 0,
        },
        {
            "category": "TEMPLATES",
            "title": "بيع قوالب ومحتوى رقمي أصلي",
            "source_url": "https://www.gumroad.com/",
            "evidence": "منصة بيع منتجات رقمية؛ إنشاء منتج لا يثبت وجود مبيعات.",
            "owner_role": "Website Builder",
            "action": "تحديد قالب رقمي يمكن إنتاجه مرة وبيعه قانونيًا، ثم اختبار الطلب قبل أي إنفاق.",
            "cost": 0,
        },
        {
            "category": "MEDIA",
            "title": "إنتاج فيديوهات قصيرة للشركات",
            "source_url": "https://www.upwork.com/nx/search/jobs/",
            "evidence": "خدمات الفيديو لها سوق على منصات العمل الحر؛ لا يُحتسب دخل إلا بعد طلب ودفع موثق.",
            "owner_role": "Cinematic Production Specialist",
            "action": "البحث عن طلبات حديثة لفيديوهات قصيرة وإعداد نموذج عرض/عينة.",
            "cost": 0,
        },
        {
            "category": "RESEARCH",
            "title": "خدمات بحث وتقارير وتنظيف بيانات",
            "source_url": "https://www.upwork.com/nx/search/jobs/",
            "evidence": "منصة عمل حر؛ المهمة أو العرض ليست إيرادًا.",
            "owner_role": "Opportunity Researcher",
            "action": "البحث عن مهام صغيرة يمكن إنجازها خلال وقت قصير وبأدوات متاحة.",
            "cost": 0,
        },
        {
            "category": "MARKETING",
            "title": "خدمة محتوى وتسويق رقمي للشركات",
            "source_url": "https://khamsat.com/",
            "evidence": "منصة خدمات؛ يجب التحقق من الطلب والبيع والدفع بشكل منفصل.",
            "owner_role": "Conversion Specialist",
            "action": "اختبار عرض خدمة واحد واضح بسعر معلن وشروط تسليم محددة.",
            "cost": 0,
        },
    )

    def __init__(self, store):
        self.store = store
        self.run_count = 0

    @staticmethod
    def _score(item: dict[str, Any]) -> float:
        # Operational priority, not a promise of profit.
        base = {
            "DIGITAL_SERVICES": 0.95,
            "LOCAL_SERVICES": 0.90,
            "RESEARCH": 0.82,
            "MEDIA": 0.78,
            "TEMPLATES": 0.70,
            "MARKETING": 0.68,
        }.get(item.get("category"), 0.5)
        return base

    def discover(self, limit: int = 8) -> list[dict[str, Any]]:
        self.run_count += 1
        chosen = self.CHANNELS[: max(1, min(int(limit), len(self.CHANNELS)))]
        created = []
        for item in chosen:
            oid = "INC-" + hashlib.sha1((item["category"]+"|"+item["title"]).encode("utf-8")).hexdigest()[:12]
            record = {
                **item,
                "opportunity_id": oid,
                "score": self._score(item),
                "status": "DISCOVERY",
                "verification_status": "UNVERIFIED",
                "verified_amount_jod": 0.0,
                "expected_value_jod": None,
                "discovered_at": time(),
                "run": self.run_count,
                "verification_rule": "لا يُحتسب أي دخل إلا بدليل طلب/معاملة ودفع مستلم قابل للمطابقة.",
            }
            self.store.upsert_income_opportunity(record)
            created.append(record)
        self.store.event("INCOME_OPPORTUNITIES_DISCOVERED", {
            "run": self.run_count, "count": len(created),
            "verified_revenue_jod": 0.0,
            "external_execution": False,
        })
        return created

    def prioritize(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.store.income_opportunities(limit)

    def verify_payment(self, opportunity_id: str, amount_jod: float, evidence: str) -> dict[str, Any]:
        amount = float(amount_jod)
        if amount <= 0 or not evidence.strip():
            return {"ok": False, "status": "REJECTED", "reason": "PAYMENT_EVIDENCE_REQUIRED"}
        rows = self.store.income_opportunities(500)
        target = next((x for x in rows if x["opportunity_id"] == opportunity_id), None)
        if not target:
            return {"ok": False, "status": "NOT_FOUND"}
        data = dict(target.get("data") or {})
        data.update({
            "status": "COMPLETED",
            "verification_status": "VERIFIED",
            "verified_amount_jod": amount,
            "payment_evidence": evidence[:2000],
        })
        self.store.upsert_income_opportunity(data)
        self.store.event("INCOME_VERIFIED", {
            "opportunity_id": opportunity_id,
            "amount_jod": amount,
            "evidence_recorded": True,
        })
        return {"ok": True, "status": "VERIFIED", "opportunity_id": opportunity_id, "amount_jod": amount}

    def snapshot(self) -> dict[str, Any]:
        summary = self.store.income_summary()
        return {
            **summary,
            "verified_revenue_jod": float(summary.get("verified", 0) or 0),
            "opportunities": self.store.income_opportunities(20),
            "principle": "الفرصة ليست دخلًا؛ الدخل لا يُحتسب قبل إثبات الدفع.",
            "run_count": self.run_count,
        }
