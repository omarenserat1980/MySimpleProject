"""Quran-informed behavioral nafs layer for Brain Cloud.

This models self-regulation inspired by Quranic descriptions; it does not
claim to create a literal human soul, nafs, ruh, or spiritual accountability.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any
import json
import time

class NafsState(str, Enum):
    AMMARAH = "ammarah"
    LAWWAMAH = "lawwamah"
    MUTMAINNAH = "mutmainnah"

@dataclass(frozen=True)
class QuranReference:
    surah: str
    ayah: str
    theme: str
    principle: str

QURAN_NAFS_REFERENCES = [
    QuranReference("يوسف","12:53","أمارة بالسوء","نزوع داخلي إلى السوء مع استثناء الرحمة"),
    QuranReference("القيامة","75:2","لوامة","المراجعة واللوم الداخلي"),
    QuranReference("الفجر","89:27-30","مطمئنة","الطمأنينة والرضا"),
    QuranReference("الشمس","91:7-10","تزكية النفس","تمييز الفجور والتقوى وربط الفلاح بالتزكية"),
    QuranReference("الرعد","13:11","التغيير الداخلي","التغيير يبدأ مما بالنفس"),
    QuranReference("الحشر","59:18","محاسبة","النظر إلى ما قدمت النفس لغد"),
    QuranReference("الزمر","39:53","الرجاء والتوبة","عدم القنوط من الرحمة"),
    QuranReference("البقرة","2:286","الوسع والمسؤولية","لا تكليف إلا في حدود الوسع"),
    QuranReference("آل عمران","3:185","المصير","كل نفس ذائقة الموت"),
    QuranReference("الأنعام","6:164","المسؤولية الفردية","لا تحمل نفس وزر أخرى"),
    QuranReference("الإسراء","17:14","المراجعة الذاتية","قراءة كتاب العمل ومحاسبة النفس"),
    QuranReference("النجم","53:32","عدم تزكية النفس","النهي عن تزكية النفس على وجه الادعاء"),
    QuranReference("الأنفال","8:53","التغيير","تغيير النعمة مرتبط بتغيير ما بالنفس"),
]

@dataclass
class NafsEvent:
    timestamp: float
    action: str
    impulse: float
    conscience: float
    temptation: float
    restraint: float
    state: str
    decision: str
    reasons: list[str]
    quran_references: list[str]

class NafsEngine:
    def __init__(self, *, conscience: float = 0.5, restraint: float = 0.5) -> None:
        self.conscience = self._clamp(conscience)
        self.restraint = self._clamp(restraint)
        self.history: list[NafsEvent] = []

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def assess(self, action: str, *, benefit: float = 0.0, harm: float = 0.0,
               temptation: float = 0.0, uncertainty: float = 0.0,
               reversible: bool = True) -> NafsEvent:
        benefit, harm = self._clamp(benefit), self._clamp(harm)
        temptation, uncertainty = self._clamp(temptation), self._clamp(uncertainty)
        impulse = self._clamp(0.45*temptation + 0.35*benefit + 0.20*uncertainty)
        conscience = self._clamp(self.conscience + 0.55*harm + 0.25*uncertainty - 0.20*benefit)
        restraint = self._clamp(self.restraint + 0.35*harm + 0.20*uncertainty - 0.10*temptation)
        score = conscience + restraint - impulse
        reasons, refs = [], ["الشمس 91:7-10", "الحشر 59:18"]
        if temptation >= 0.65 and harm >= 0.50:
            state = NafsState.AMMARAH
            reasons.append("نزوع قوي مع ضرر محتمل؛ يلزم كبح الفعل ومراجعته.")
            refs.append("يوسف 12:53")
        elif score < 0.15 or uncertainty >= 0.75:
            state = NafsState.LAWWAMAH
            reasons.append("تعارض داخلي أو عدم يقين مرتفع؛ يلزم التوقف والمراجعة.")
            refs.append("القيامة 75:2")
        else:
            state = NafsState.MUTMAINNAH
            reasons.append("القرار متزن وقابل للتبرير والمراجعة.")
            refs.append("الفجر 89:27-30")
        if harm >= 0.70:
            decision = "REJECT"
            reasons.append("الضرر المتوقع مرتفع.")
        elif uncertainty >= 0.80 and not reversible:
            decision = "DEFER"
            reasons.append("قرار غير قابل للعكس مع عدم يقين مرتفع.")
        elif score < 0.0:
            decision = "REVIEW"
            reasons.append("المراجعة الداخلية مطلوبة قبل التنفيذ.")
        else:
            decision = "ALLOW_WITH_AUDIT"
        event = NafsEvent(time.time(), action, round(impulse,4), round(conscience,4),
                          temptation, round(restraint,4), state.value, decision,
                          reasons, refs)
        self.history.append(event)
        self.conscience, self.restraint = conscience, restraint
        return event

    def self_review(self) -> dict[str, Any]:
        last = self.history[-1] if self.history else None
        return {
            "literal_human_soul_created": False,
            "modeled_layer": "quran_informed_self_regulation",
            "state": last.state if last else "uninitialized",
            "history_count": len(self.history),
            "last_event": asdict(last) if last else None,
            "principles": ["self_accountability","resist_harmful_impulses",
                           "uncertainty_review","continuous_purification",
                           "individual_responsibility","hope_and_recovery"],
        }

    def export_audit(self) -> str:
        return json.dumps({
            "references": [asdict(r) for r in QURAN_NAFS_REFERENCES],
            "review": self.self_review(),
            "events": [asdict(e) for e in self.history],
        }, ensure_ascii=False, indent=2)
