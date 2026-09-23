"""Topic sources for the background cinematic factory.

Environment topics take priority. A small evergreen fallback keeps the factory
able to produce without requiring another paid service or manual intervention.
"""
from __future__ import annotations
import json, os
from typing import Any, Sequence

DEFAULT_TOPICS = [
    {"title": "الطريق الذي لا يظهر إلا بعد أن تبدأ", "objective": "قصة سينمائية عن الشجاعة في اتخاذ أول خطوة", "expected_value_jod": 25, "effort_hours": 2, "evidence": .6, "repeatability": .9, "risk": .2, "freshness": .8, "route": "youtube"},
    {"title": "ساعة واحدة قبل فوات الأوان", "objective": "قصة تشويقية عن قرار مصيري خلال ساعة واحدة", "expected_value_jod": 25, "effort_hours": 2, "evidence": .5, "repeatability": .85, "risk": .25, "freshness": .9, "route": "youtube"},
    {"title": "المدينة التي نسيت صوتها", "objective": "حكاية خيالية سينمائية عن مدينة تستعيد صوتها", "expected_value_jod": 25, "effort_hours": 2.5, "evidence": .4, "repeatability": .8, "risk": .25, "freshness": .9, "route": "youtube"},
    {"title": "رسالة وصلت بعد عشرين عامًا", "objective": "دراما غامضة حول رسالة تغيّر قرارًا قديمًا", "expected_value_jod": 25, "effort_hours": 2.5, "evidence": .5, "repeatability": .85, "risk": .2, "freshness": .9, "route": "youtube"},
]

class EnvTopicResearcher:
    def discover(self, *, audience: str, limit: int = 10) -> Sequence[dict[str, Any]]:
        raw = os.getenv("FACTORY_TOPICS_JSON", "").strip()
        if raw:
            try:
                items = json.loads(raw)
                if isinstance(items, list) and items:
                    return items[:limit]
            except Exception:
                pass
        return DEFAULT_TOPICS[:limit]
