"""Verified-income engine for Electronic Brain V12.

The engine separates opportunity discovery from revenue recognition. It creates
auditable, low-cost experiments, records evidence, and never counts expected
money as received money.
"""
from __future__ import annotations

from time import time
from typing import Any
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


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
        {
            "category": "WEBSITE_SETUP", "title": "إعداد صفحة هبوط عربية للأعمال",
            "source_url": "https://mostaql.com/", "evidence": "قناة بحث عن مشاريع؛ ليست عملية بيع بحد ذاتها.",
            "owner_role": "Web Builder", "action": "استهداف طلبات صفحات الهبوط والمواقع التعريفية الصغيرة.", "cost": 0,
        },
        {
            "category": "SEO", "title": "تحسين ظهور موقع محلي في البحث",
            "source_url": "https://khamsat.com/", "evidence": "قناة خدمات؛ يلزم طلب وقبول ودفع موثق.",
            "owner_role": "SEO Specialist", "action": "تجهيز خدمة تدقيق SEO وإصلاحات أساسية للأعمال الصغيرة.", "cost": 0,
        },
        {
            "category": "PRODUCT_LISTING", "title": "كتابة ووصف منتجات للمتاجر",
            "source_url": "https://www.upwork.com/nx/search/jobs/", "evidence": "قناة بحث عن وظائف؛ لا تعني وجود عميل أو دفع.",
            "owner_role": "Content Specialist", "action": "البحث عن مهام إدخال ووصف المنتجات العربية.", "cost": 0,
        },
        {
            "category": "ARABIC_CONTENT", "title": "كتابة محتوى عربي قصير",
            "source_url": "https://mostaql.com/", "evidence": "مشاريع العمل الحر تحتاج تحققًا من الطلب والميزانية.",
            "owner_role": "Arabic Content Specialist", "action": "البحث عن مهام كتابة وصف وإعلانات ومنشورات عربية.", "cost": 0,
        },
        {
            "category": "TRANSLATION", "title": "ترجمة عربية/إنجليزية لمحتوى قصير",
            "source_url": "https://www.upwork.com/nx/search/jobs/", "evidence": "قناة بحث؛ لا تُحسب فرصة مدفوعة إلا بعد قبول العميل.",
            "owner_role": "Arabic Translation Specialist", "action": "البحث عن نصوص قصيرة مناسبة للقدرة المتاحة.", "cost": 0,
        },
        {
            "category": "DATA_ENTRY", "title": "إدخال وتنظيم بيانات",
            "source_url": "https://www.upwork.com/nx/search/jobs/", "evidence": "قناة وظائف؛ التقديم لا يثبت الدخل.",
            "owner_role": "Data Specialist", "action": "استهداف مهام صغيرة قابلة للتسليم والمراجعة.", "cost": 0,
        },
        {
            "category": "SOCIAL_MEDIA", "title": "إعداد منشورات وصفحات أعمال",
            "source_url": "https://khamsat.com/", "evidence": "خدمة محتملة؛ البيع والدفع يحتاجان إثباتًا منفصلًا.",
            "owner_role": "Social Media Specialist", "action": "تجهيز باقة منشورات بسيطة للأعمال المحلية.", "cost": 0,
        },
        {
            "category": "E_COMMERCE", "title": "تهيئة متجر إلكتروني بسيط",
            "source_url": "https://mostaql.com/", "evidence": "قناة مشاريع؛ يجب التحقق من المشروع قبل التقديم.",
            "owner_role": "E-commerce Specialist", "action": "البحث عن متاجر تحتاج إعدادًا أو تحسينًا محدودًا.", "cost": 0,
        },
        {
            "category": "AUTOMATION", "title": "أتمتة مهام إدارية صغيرة",
            "source_url": "https://www.upwork.com/nx/search/jobs/", "evidence": "قناة وظائف؛ لا يوجد دخل مثبت قبل قبول ودفع.",
            "owner_role": "Automation Specialist", "action": "البحث عن مهام أتمتة بسيطة يمكن اختبارها قبل التسليم.", "cost": 0,
        },
        {
            "category": "VIDEO_EDITING", "title": "مونتاج فيديوهات قصيرة وإعلانات",
            "source_url": "https://khamsat.com/", "evidence": "خدمة رقمية محتملة؛ يجب التحقق من الطلب والبيع والدفع.",
            "owner_role": "Video Editor", "action": "استهداف فيديوهات قصيرة وإعلانات منتجات.", "cost": 0,
        },
        {
            "category": "PRESENTATIONS", "title": "تصميم عروض تقديمية عربية",
            "source_url": "https://www.upwork.com/nx/search/jobs/", "evidence": "قناة بحث عن أعمال؛ ليست مبيعات مؤكدة.",
            "owner_role": "Presentation Designer", "action": "البحث عن عروض صغيرة يمكن إنتاجها بسرعة.", "cost": 0,
        },
        {
            "category": "DOCUMENT_FORMATTING", "title": "تنسيق مستندات وتقارير",
            "source_url": "https://mostaql.com/", "evidence": "مشاريع محتملة تحتاج قبولًا ودفعًا موثقًا.",
            "owner_role": "Document Specialist", "action": "استهداف أعمال تنسيق مستندات عربية وجداول وتقارير.", "cost": 0,
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

    def discover(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return research channels only; never store a channel as a live opportunity."""
        self.run_count += 1
        channels = [dict(x, source_kind="SEARCH_CHANNEL") for x in self.CHANNELS[: max(1, min(int(limit), len(self.CHANNELS)))]]
        self.store.event("INCOME_SEARCH_PLAN_CREATED", {"run": self.run_count, "channels": len(channels), "persisted_as_opportunities": False})
        return channels

    @staticmethod
    def _canonical_url(url: str) -> str:
        parts = urlsplit(str(url).strip())
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return ""
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "ref"}]
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))

    @staticmethod
    def _fit_score(title: str, requirements: str, category: str) -> tuple[float, list[str]]:
        text = f"{title} {requirements} {category}".lower()
        groups = {
            "web": ("website", "web", "wordpress", "html", "css", "javascript", "موقع", "ويب"),
            "python": ("python", "fastapi", "django", "flask"),
            "dotnet": (".net", "asp.net", "c#", "csharp", "dotnet"),
            "api": ("api", "rest", "integration", "ربط", "واجهة"),
            "automation": ("automation", "automate", "أتمتة"),
            "ecommerce": ("ecommerce", "shopify", "woocommerce", "متجر", "products"),
            "arabic": ("arabic", "عربي", "العربية"),
            "data": ("data entry", "excel", "إدخال بيانات"),
        }
        hits = [name for name, words in groups.items() if any(w in text for w in words)]
        score = min(100.0, 20.0 + len(hits) * 11.0)
        if any(x in text for x in ("senior", "5+ years", "5 years", "خبير 5", "خبرة 5")):
            score -= 15
        if any(x in text for x in ("urgent", "عاجل", "today", "اليوم")):
            score -= 5
        return max(0.0, score), hits

    @staticmethod
    def _freshness(retrieved_at: str, max_age_hours: float) -> bool:
        try:
            dt = datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).total_seconds() <= max_age_hours * 3600
        except Exception:
            return False

    def ingest_live_opportunities(self, results: list[dict[str, Any]], max_age_hours: float = 72) -> list[dict[str, Any]]:
        """Persist only evidence-backed, fresh, externally discovered job/project records."""
        accepted = []; self.run_count += 1
        for raw in results or []:
            item = dict(raw or {})
            title = str(item.get("title") or "").strip(); url = str(item.get("url") or item.get("source_url") or "").strip()
            retrieved_at = str(item.get("retrieved_at") or "").strip(); requirements = str(item.get("requirements") or "").strip(); budget = item.get("budget")
            if not title or not url.startswith(("http://","https://")) or not retrieved_at or not self._freshness(retrieved_at, max_age_hours): continue
            if not requirements and budget in (None, ""): continue
            canonical_url = self._canonical_url(url)
            if not canonical_url:
                continue
            source_text = re.sub(r"\s+", " ", str(item.get("source") or canonical_url))[:300]
            fingerprint = hashlib.sha1(canonical_url.encode("utf-8")).hexdigest()[:12]
            existing = next((x for x in self.store.income_opportunities(500)
                             if x.get("opportunity_id") == "LIVE-" + fingerprint), None)
            if existing and existing.get("data", {}).get("retrieved_at") == retrieved_at:
                continue
            fit_score, fit_matches = self._fit_score(title, requirements, str(item.get("category") or "FREELANCE_JOB"))
            history = list((existing or {}).get("data", {}).get("research_history", []))
            previous_title = str((existing or {}).get("title") or (existing or {}).get("data", {}).get("title") or "")
            previous_req = str((existing or {}).get("data", {}).get("requirements") or "")
            previous_budget = (existing or {}).get("data", {}).get("budget")
            previous_posted = (existing or {}).get("data", {}).get("posted_at")
            content_payload = {
                "title": title,
                "requirements": requirements,
                "budget": budget,
                "posted_at": item.get("posted_at"),
            }
            content_hash = hashlib.sha256(
                repr(sorted(content_payload.items())).encode("utf-8")
            ).hexdigest()[:16]
            previous_hash = str((existing or {}).get("data", {}).get("content_hash") or "")
            changed = bool(existing) and (
                previous_hash != content_hash
                if previous_hash
                else (previous_title != title or previous_req != requirements
                      or previous_budget != budget or previous_posted != item.get("posted_at"))
            )
            lifecycle = "UPDATED" if changed else ("UNCHANGED" if existing else "NEW")
            history.append({"retrieved_at": retrieved_at, "title": title[:300], "score": fit_score, "lifecycle": lifecycle})
            history = history[-10:]
            record = {"opportunity_id":"LIVE-"+fingerprint,"category":str(item.get("category") or "FREELANCE_JOB"),"title":title[:300],"source_url":canonical_url,
                      "evidence":f"مصدر حي: {source_text}; retrieved_at={retrieved_at}; هذه فرصة معلنة وليست إيرادًا.","requirements":requirements[:4000],"budget":budget,
                      "posted_at":item.get("posted_at"),"retrieved_at":retrieved_at,"source_kind":"LIVE_OPPORTUNITY","status":"DISCOVERY",
                      "score":fit_score,"fit_matches":fit_matches,"lifecycle":lifecycle,"verification_status":"UNVERIFIED","verified_amount_jod":0.0,"expected_value_jod":None,
                      "owner_role":"Opportunity Researcher","discovered_at":time(),"run":self.run_count,
                      "research_history":history,"content_hash":content_hash,
                      "verification_rule":"لا يُحتسب أي دخل إلا بدليل قبول ثم دفع مستلم قابل للمطابقة."}
            self.store.upsert_income_opportunity(record); accepted.append(record)
        self.store.event("LIVE_INCOME_OPPORTUNITIES_INGESTED", {"run":self.run_count,"accepted":len(accepted),"received":len(results or []),"external_execution":False})
        return accepted

    def refresh_lifecycle(self, max_age_hours: float = 72, limit: int = 500) -> dict[str, Any]:
        """Mark stale live opportunities without overwriting verified/completed income."""
        now = datetime.now(timezone.utc)
        rows = self.store.income_opportunities(max(1, min(int(limit), 500)))
        stale = 0
        checked = 0
        for row in rows:
            data = dict(row.get("data") or {})
            if data.get("source_kind") != "LIVE_OPPORTUNITY":
                continue
            checked += 1
            lifecycle = str(data.get("lifecycle") or "UNKNOWN")
            if lifecycle == "STALE":
                stale += 1
                continue
            if data.get("verification_status") == "VERIFIED" or str(data.get("status")) in {"COMPLETED", "PAYMENT_VERIFIED"}:
                continue
            retrieved_at = str(data.get("retrieved_at") or "")
            if not retrieved_at or not self._freshness(retrieved_at, max_age_hours):
                data["lifecycle"] = "STALE"
                data["status"] = "STALE"
                data["stale_at"] = now.isoformat()
                data["stale_after_hours"] = max_age_hours
                self.store.upsert_income_opportunity(data)
                self.store.event("INCOME_OPPORTUNITY_STALE", {
                    "opportunity_id": data.get("opportunity_id"),
                    "max_age_hours": max_age_hours,
                })
                stale += 1
        return {"ok": True, "checked": checked, "stale": stale, "max_age_hours": max_age_hours}

    def lifecycle_report(self, limit: int = 100) -> dict[str, Any]:
        rows = self.store.income_opportunities(limit)
        counts = {"NEW": 0, "UPDATED": 0, "UNCHANGED": 0, "STALE": 0, "UNKNOWN": 0}
        for row in rows:
            data = row.get("data") or {}
            lifecycle = str(data.get("lifecycle") or "UNKNOWN")
            if lifecycle not in counts:
                lifecycle = "UNKNOWN"
            counts[lifecycle] += 1
        return {"ok": True, "counts": counts, "opportunities": rows}

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


    def verified_total(self):
        """Return only revenue explicitly recorded as verified by the engine ledger."""
        summary = self.store.income_summary()
        return float(summary.get("verified", 0) or 0)
