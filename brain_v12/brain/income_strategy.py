"""Income-first operating strategy for Electronic Brain V12.

This module turns the verified-income engine into an explicit execution priority:
find small, realistic opportunities first, prepare evidence-backed offers, verify
payment, and only then count revenue. It does not fabricate sales or perform
external transactions.
"""
from __future__ import annotations

from time import time
from typing import Any


class IncomeStrategy:
    TARGET_JOD = 10.0

    STAGES = (
        ("DISCOVER", "ابحث عن فرص حقيقية حديثة وقابلة للتنفيذ وبميزانية صغيرة."),
        ("QUALIFY", "استبعد الفرص الغامضة أو غير المناسبة للمهارات أو التي تحتاج إنفاقًا مقدمًا."),
        ("PACKAGE", "جهّز عرضًا قصيرًا واضحًا وعينة/نموذجًا مناسبًا للطلب."),
        ("SUBMIT", "قدّم العرض فقط عبر قناة تسمح للمستخدم أو لصاحب الحساب بإرساله."),
        ("DELIVER", "نفّذ العمل المتفق عليه بجودة قابلة للتحقق."),
        ("VERIFY", "تحقق من استلام الدفع ودليله قبل تسجيل أي إيراد."),
        ("LEARN", "قارن ما نجح وما لم ينجح وأعد ترتيب القنوات."),
    )

    PRIORITY = (
        {
            "rank": 1,
            "channel": "UPWORK_SMALL_FIXED",
            "why": "مهام صغيرة محددة يمكن أن تتجاوز هدف 10 JOD إذا تم الفوز بها.",
            "query": 'site:upwork.com/freelance-jobs "fixed-price" WordPress $20',
        },
        {
            "rank": 2,
            "channel": "ARABIC_DIGITAL_SERVICE",
            "why": "خدمة عربية بسيطة يمكن تسليمها بسرعة وبتكلفة تشغيل شبه صفرية.",
            "query": "خدمات عربية تصميم موقع صفحة هبوط أتمتة",
        },
        {
            "rank": 3,
            "channel": "LOCAL_BUSINESS_LEADS",
            "why": "عملاء محليون يمكن تقديم خدمة رقمية صغيرة لهم دون شراء مخزون.",
            "query": "شركات إربد الأردن مطاعم عيادات مواقع ويب",
        },
        {
            "rank": 4,
            "channel": "SHORT_VIDEO",
            "why": "إنتاج فيديو قصير يمكن تسليمه بسرعة باستخدام أدوات متاحة.",
            "query": 'site:upwork.com/freelance-jobs "short video" fixed-price',
        },
        {
            "rank": 5,
            "channel": "RESEARCH_DATA",
            "why": "مهام بحث/تنظيف بيانات صغيرة يمكن إنجازها دون تكلفة مادية كبيرة.",
            "query": 'site:upwork.com/freelance-jobs research data fixed-price $20',
        },
        {
            "rank": 6,
            "channel": "TEMPLATES",
            "why": "منتج رقمي قابل للتكرار، لكنه أبطأ عادة من خدمة مباشرة للوصول لأول دفعة.",
            "query": "Arabic digital templates sell online",
        },
        {
            "rank": 7,
            "channel": "YOUTUBE",
            "why": "قناة طويلة الأجل؛ لا تُعامل كخطة للحصول على أول 10 JOD سريعًا.",
            "query": "YouTube monetization Jordan requirements",
        },
    )

    PROMPTS = {
        "researcher": (
            "أنت باحث فرص دخل. ابحث فقط عن فرص حقيقية حديثة ومعلنة. "
            "لكل فرصة سجّل الرابط، تاريخ/حداثة الدليل، المطلوب، الميزانية إن وجدت، "
            "المهارات، القيود، وهل يمكن تنفيذها بالأدوات المتاحة. لا تعتبر الإعلان دخلاً."
        ),
        "qualifier": (
            "أنت محلل تأهيل. رتّب الفرص حسب سهولة التنفيذ، قربها من مهاراتنا، "
            "الميزانية، سرعة التسليم، تكلفة الحصول على العميل، واحتمال وجود دفع موثق. "
            "لا تستخدم كلمة مضمون أو مؤكد للقبول."
        ),
        "offer_writer": (
            "أنت كاتب عروض. أنشئ عرضًا قصيرًا صادقًا يطابق متطلبات الفرصة فقط، "
            "مع نطاق واضح ومدة وتسليم وسعر مقترح. لا تدّع خبرة أو نتائج غير مثبتة."
        ),
        "executor": (
            "أنت منفذ خدمات. نفّذ فقط العمل الذي تم قبوله فعليًا، واحفظ مخرجات قابلة "
            "للمراجعة، ولا تعتبر المهمة مكتملة قبل التحقق من متطلبات العميل."
        ),
        "verifier": (
            "أنت مدقق الإيراد. لا تسجل أي JOD كإيراد إلا بعد وجود دليل دفع قابل للمطابقة. "
            "إذا كان الدليل ناقصًا فالحالة UNVERIFIED ويبقى المبلغ صفرًا."
        ),
        "optimizer": (
            "أنت محلل تعلم. بعد كل تجربة قارن الفرصة والعرض والنتيجة والدفع، "
            "ثم حدّث أولوية القنوات دون تضخيم النتائج."
        ),
    }

    def __init__(self, income_engine):
        self.income_engine = income_engine

    def mission(self) -> dict[str, Any]:
        snap = self.income_engine.snapshot()
        verified = float(snap.get("verified_revenue_jod", 0.0) or 0.0)
        return {
            "ok": True,
            "mission": "FIRST_VERIFIED_10_JOD",
            "target_jod": self.TARGET_JOD,
            "verified_revenue_jod": verified,
            "gap_jod": max(0.0, self.TARGET_JOD - verified),
            "priority": list(self.PRIORITY),
            "stages": [{"stage": s, "objective": o} for s, o in self.STAGES],
            "prompts": dict(self.PROMPTS),
            "rules": [
                "الفرصة ليست دخلاً.",
                "العرض ليس بيعًا.",
                "العمل المقبول ليس إيرادًا.",
                "الإيراد لا يُسجل قبل دليل دفع قابل للمطابقة.",
                "لا شراء إعلانات أو مخزون أو اشتراكات مدفوعة لتحقيق الهدف الأول.",
                "لا مراسلات أو تعاقدات أو تحويلات مالية تلقائية خارج الصلاحيات.",
            ],
            "next_actions": [
                "البحث الحي عن فرص صغيرة حديثة.",
                "تأهيل أعلى الفرص.",
                "تجهيز عرض وعينة لكل فرصة مؤهلة.",
                "تسجيل حالة التقديم والنتيجة.",
                "تنفيذ المقبول فقط.",
                "التحقق من الدفع ثم تسجيله.",
            ],
            "generated_at": time(),
        }

    def search_plan(self) -> dict[str, Any]:
        return {
            "ok": True,
            "objective": "العثور على أول فرصة مدفوعة قابلة للتحقق بقيمة لا تقل عن 10 JOD دون إنفاق مقدم.",
            "queries": [x["query"] for x in self.PRIORITY],
            "sources": [
                "Upwork",
                "خمسات",
                "مستقل",
                "مصادر الأعمال المحلية العلنية",
                "منصات المنتجات الرقمية",
            ],
            "evidence_required": ["url", "title", "requirements", "budget_or_price", "retrieved_at"],
            "note": "هذا مخطط بحث؛ نتائج البحث الخارجية يجب إدخالها مع دليلها ولا تُعامل كإيراد.",
        }
