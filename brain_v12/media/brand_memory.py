"""Brand memory: approved facts and messaging constraints for company media."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class BrandMemory:
    company_name: str
    approved_facts: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    tone: str = "clear, factual, professional"
    prohibited_claims: list[str] = field(default_factory=list)

    def fact_check(self, text: str) -> dict:
        lowered = text.lower()
        prohibited = [x for x in self.prohibited_claims if x.lower() in lowered]
        return {"approved": not prohibited, "prohibited_matches": prohibited}
