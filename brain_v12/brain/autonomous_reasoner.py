"""BRAIN Autonomous Reasoner: evidence-driven observe -> diagnose -> test -> repair -> verify loop."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import json,time
from pathlib import Path

@dataclass
class ReasoningDecision:
    phase:str
    action:str
    reason:str
    confidence:str
    required_tests:list[str]
    evidence_ids:list[str]

class AutonomousReasoner:
    """Deterministic policy layer; it never treats a green workflow as proof by itself."""
    TEST_MAP={
      "CODE_OR_LOGIC":["compile","unit"],
      "MEDIA_PIPELINE":["compile","cinematic_qc","media_probe"],
      "INPUT_OR_ARTIFACT":["artifact_integrity","manifest_consistency"],
      "DEPENDENCY_OR_IMPORT":["compile","dependency_import"],
      "EXECUTION_INFRA":["health","workflow_status"],
      "UNKNOWN":["compile","self_test","full_verification"],
    }
    def observe(self, evidence):
        failures=evidence.get("failures",[])
        if not failures:return ReasoningDecision("observe","verify","no_known_failure","high",["self_test"],[])
        return self.diagnose(evidence)
    def diagnose(self,evidence):
        failures=evidence.get("failures",[])
        classes=[str(x.get("class","UNKNOWN")).upper() for x in failures]
        kind=next((x for x in ("MEDIA_PIPELINE","INPUT_OR_ARTIFACT","DEPENDENCY_OR_IMPORT","EXECUTION_INFRA","CODE_OR_LOGIC") if x in classes),"UNKNOWN")
        tests=self.TEST_MAP[kind]
        return ReasoningDecision("diagnose","repair",f"failure_class={kind}","medium" if kind!="UNKNOWN" else "low",tests,[str(x.get("id","")) for x in failures])
    def next(self,evidence):
        d=self.observe(evidence)
        if d.action=="verify" and evidence.get("verified"): return ReasoningDecision("deliver","deliver","independent verification passed","high",[],[])
        if evidence.get("attempts",0)>=evidence.get("max_attempts",3): return ReasoningDecision("blocked","block","attempt budget exhausted","high",d.required_tests,d.evidence_ids)
        return d
    def explain(self,d): return asdict(d)

def write_decision(root,decision):
    p=Path(root)/"reasoning.json";p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(asdict(decision),ensure_ascii=False,indent=2),encoding="utf-8")
    return p
