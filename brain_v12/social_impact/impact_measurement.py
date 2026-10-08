"""Evidence-based social impact measurement primitives."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ImpactMetric:
    metric_id:str
    definition:str
    baseline:float
    target:float
    observed:float|None=None
    source:str=""

def progress(m:ImpactMetric)->float:
    if m.target==m.baseline: return 1.0 if m.observed==m.target else 0.0
    if m.observed is None: return 0.0
    return (m.observed-m.baseline)/(m.target-m.baseline)
