from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
from .models import EvidenceLevel,QuranicFinding

@dataclass(frozen=True)
class KnowledgeOpportunity:
    id:str
    type:str
    title:str
    rationale:str
    evidence_levels:tuple[str,...]
    requires_review:bool=True

class KnowledgeOpportunityEngine:
    TYPES=("research_question","education","social_good","accessibility")
    def generate(self,finding:QuranicFinding)->dict:
        levels=tuple(dict.fromkeys(e.level.value for e in finding.evidence))
        base=finding.finding.strip()
        items=[
            KnowledgeOpportunity("","research_question","سؤال بحثي مشتق من النتيجة",
                f"تحويل النتيجة إلى سؤال قابل للاختبار دون نسبته إلى الوحي: {base}",levels),
            KnowledgeOpportunity("","education","مسار تعليمي",
                f"بناء مادة تعليمية تشرح الأدلة وحدودها: {base}",levels),
            KnowledgeOpportunity("","social_good","فكرة منفعة اجتماعية",
                f"اختبار منفعة عملية للناس مستندة إلى المعرفة المتاحة: {base}",levels),
            KnowledgeOpportunity("","accessibility","أداة إتاحة",
                f"استكشاف طريقة لجعل المعرفة أكثر إتاحة وفهمًا: {base}",levels),
        ]
        out=[]
        for x in items:
            oid=sha256(f"{x.type}|{x.title}|{x.rationale}".encode()).hexdigest()[:16]
            out.append({**asdict(x),"id":oid})
        return {"status":"IDEAS_ONLY","opportunities":out,
                "rule":"opportunities are hypotheses for human evaluation, not religious rulings"}
