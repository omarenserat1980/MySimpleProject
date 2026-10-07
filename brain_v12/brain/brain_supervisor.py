"""Brain Supervisor: bounded autonomous orchestration over the existing Control Plane."""
from __future__ import annotations
import json, time
from pathlib import Path
from .autonomy_control_plane import ControlPlane
from .autonomous_reasoner import AutonomousReasoner
from .execution_gateway import BrainExecutionGateway
from .execution_contract import ExecutionContract
from .reality_core import Observation, RealityCore
from .brain_constitution import BrainConstitution
from .mission import Mission
from ..self_healing.problem_completion_gate import CompletionContract, ProblemCompletionGate
from ..self_healing.emergency_resource_guard import EmergencyResourceGuard

SAFE_EXTERNAL_ACTIONS={"submit_application","publish_external","move_money","withdraw"}

class BrainSupervisor:
    """Single authoritative orchestrator. V13 primitives are policy/state layers only."""
    def __init__(self,root="brain6_artifacts/supervisor",max_cycles=5,execution_gateway=None):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.state_path=self.root/"state.json"; self.events_path=self.root/"events.jsonl"
        self.max_cycles=max(1,min(int(max_cycles),5))
        self.control=ControlPlane(str(self.root/"control_plane")); self.reasoner=AutonomousReasoner()
        self.execution_gateway=execution_gateway or BrainExecutionGateway(); self.resource_guard=EmergencyResourceGuard()
        self.reality=RealityCore(); self.constitution=BrainConstitution(); self.missions={}

    def _event(self,job_id,event,data=None):
        row={"ts":time.time(),"job_id":job_id,"event":event,"data":data or {}}
        with self.events_path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")

    def create(self,task,steps=None,budget=8):
        steps=steps or ["discover","plan","select_backend","execute","verify","repair","retry","deliver"]
        job=self.control.create(task,steps,max_attempts=self.max_cycles,budget=budget); job=self.control.start_attempt(job)
        self.missions[job["job_id"]]=Mission(job["job_id"],task,max_attempts=self.max_cycles)
        self._event(job["job_id"],"supervisor_created",{"steps":steps,"v13":"enabled"}); return job

    def execution_contract(self,job,action,executor="brain-supervisor",risk="LOW",expected_results=()):
        c=ExecutionContract(job["job_id"],job["job_id"],action,executor,expected_results=tuple(expected_results),risk=risk,
                             idempotency_key=f"{job['job_id']}:{action}:{job.get('attempts',0)}")
        c.validate(); self._event(job["job_id"],"execution_contract",c.as_dict()); return c

    def observe(self,job_id,key,value,source="supervisor",confidence=1.0,evidence_ids=()):
        obs=self.reality.observe(Observation(key,value,source=source,confidence=confidence,evidence_ids=tuple(evidence_ids)))
        self._event(job_id,"observation",{"key":key,"kind":obs.kind.value,"confidence":obs.normalized_confidence()}); return obs

    def transition(self,job,phase,status="running",details=None,enforce_authority=True):
        allowed={"discover","plan","select_backend","execute","verify","repair","retry","deliver","blocked","completed","failed"}
        if phase not in allowed:raise ValueError("unknown_supervisor_phase")
        if phase in {"execute","retry"} and enforce_authority:
            resource=self.resource_guard.sample()
            if resource.get("emergency"): details={"emergency":"RESOURCE_OVERLOAD","resource":resource,"previous_phase":phase}; phase="blocked"; status="blocked"
        if phase=="execute" and enforce_authority:
            self.execution_gateway.authorize("brain-internal-execution"); self.execution_contract(job,"execute")
        row=dict(job); row.update(phase=phase,status=status,updated_at=time.time(),details=details or {})
        idx={"discover":0,"plan":1,"select_backend":2,"execute":3,"verify":4,"repair":5,"retry":6,"deliver":7}.get(phase,row.get("step_index",0))
        if idx>=row.get("step_index",0):row=self.control.checkpoint(row,idx,row["details"])
        if status in {"blocked","failed","completed"}:row["status"]=status;self.control._append(self.control.jobs,row)
        self._event(row["job_id"],"phase",{"phase":phase,"status":status,"details":row["details"]});return row

    def reason(self,evidence):
        decision=self.reasoner.next(evidence);self._event(evidence.get("job_id","unknown"),"reasoning_decision",self.reasoner.explain(decision));return decision

    def _completion_decision(self,verification):
        c=verification.get("completion_contract")
        if not c:return None
        gate=ProblemCompletionGate(CompletionContract(desired=c.get("desired",{}),invariants=c.get("invariants",{}),evidence_required=c.get("evidence_required",True)))
        return gate.decision(verification.get("verified_world",{}),verification.get("evidence",verification))

    def next_action(self,job,verification):
        completion=self._completion_decision(verification)
        if completion:
            if completion["action"]=="deliver":return {"action":"deliver","reason":"verified_problem_completion","completion":completion}
            if job.get("attempts",0)>=job.get("max_attempts",self.max_cycles):return {"action":"blocked","reason":"attempt_limit_after_reality_check","completion":completion}
            return {"action":"treat","reason":"problem_not_complete","completion":completion}
        if verification.get("verified") or verification.get("ok"):return {"action":"deliver","reason":"verified"}
        if job.get("attempts",0)>=job.get("max_attempts",self.max_cycles):return {"action":"blocked","reason":"attempt_limit"}
        return self.decide_repair(verification)

    def repair_and_retry(self,job,verification):
        action=self.next_action(job,verification)
        if action["action"]=="deliver":return self.transition(job,"deliver",status="completed",details=action)
        if action["action"]=="blocked":return self.transition(job,"blocked",status="blocked",details=action)
        repaired=self.transition(job,"repair",details=action);retried=self.control.start_attempt(repaired)
        self._event(retried["job_id"],"repair_retry_started",action);return self.transition(retried,"retry",details={"action":action["action"],"completion":action.get("completion")})

    def decide_repair(self,verification):
        if verification.get("ok"):return {"action":"none","reason":"verified"}
        repair=verification.get("repair_action")
        if repair in {"rebuild_artifact","retry_backend","fallback_renderer","fix_manifest"}:return {"action":repair,"reason":"bounded_repair"}
        return {"action":"retry_backend","reason":"generic_retry"}

    def authorize_external(self,action,approved=False):
        if action not in SAFE_EXTERNAL_ACTIONS:return {"allowed":False,"reason":"unknown_external_action"}
        if not approved:return {"allowed":False,"reason":"policy_gate_required"}
        return {"allowed":True,"reason":"explicit_approval"}

    def snapshot(self,job,outcome=None):
        data={"generated_at":time.time(),"job":job,"outcome":outcome or {},"reality":self.reality.snapshot()}
        self.state_path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");return data

    def run_simulation(self,task,verification_ok=True):
        job=self.create(task)
        for phase in ["discover","plan","select_backend","execute","verify"]:job=self.transition(job,phase,details={"simulated":True},enforce_authority=False)
        verification={"ok":bool(verification_ok)}
        if not verification["ok"]:
            job=self.transition(job,"repair",details=self.decide_repair(verification));job=self.transition(job,"retry",details={"bounded":True})
            job=self.transition(job,"execute",details={"retry":True},enforce_authority=False);job=self.transition(job,"verify",details={"retry":True})
        final="completed" if verification_ok else "completed_after_repair"
        job=self.transition(job,"deliver",status="completed",details={"result":final});self.snapshot(job,{"verified":verification_ok,"result":final});return job

if __name__=="__main__":print(json.dumps(BrainSupervisor().run_simulation("supervisor_smoke_test"),indent=2))
