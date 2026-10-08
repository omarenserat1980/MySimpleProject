"""Macroeconomic and business-economy analysis."""
from dataclasses import dataclass

@dataclass(frozen=True)
class EconomicAnalysis:
    geography:str
    period:str
    indicators:tuple[str,...]
    drivers:tuple[str,...]
    risks:tuple[str,...]
    evidence_refs:tuple[str,...]

def ready(x:EconomicAnalysis)->bool:
    return bool(x.geography and x.period and x.indicators and x.evidence_refs)
