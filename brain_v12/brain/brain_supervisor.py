"""Brain Supervisor: bounded autonomous orchestration over the existing Control Plane."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from .autonomy_control_plane import ControlPlane
from .autonomous_reasoner import AutonomousReasoner
from .execution_gateway import BrainExecutionGateway
from .execution_contract import ExecutionContract
from .reality_core import Observation, RealityCore
from .brain_constitution import BrainConstitution
from .mission import Mission
from .evidence_store import EvidenceStore
from .verification_core import VerificationCore
from .golden_acceptance_gate import GoldenAcceptanceGate
from .asic_resource_adapter import ASICResourceAdapter
from ..self_healing.problem_completion_gate import CompletionContract, ProblemCompletionGate
from ..self_healing.emergency_resource_guard import EmergencyResourceGuard

SAFE_EXTERNAL_ACTIONS={"submit_application","publish_external","move_money","withdraw"}

class BrainSupervisor:
    """Single authoritative orchestrator. V13 primitives are policy/state layers only."""
    def __init__(self,root=None,max_cycles=5,execution_gateway=None):
        if root is None:
            root = os.getenv("BRAIN_SUPERVISOR_ROOT")
        if root is None:
            runtime_home = Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser()
            root = runtime_home / "brain6_artifacts" / "supervisor"
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.state_path=self.root/"state.json"; self.events_path=self.root/"events.jsonl"
        self.max_cycles=max(1,min(int(max_cycles),5))
        self.control=ControlPlane(str(self.root/"control_plane")); self.reasoner=AutonomousReasoner()
        self.execution_gateway=execution_gateway or BrainExecutionGateway(); self.resource_guard=EmergencyResourceGuard()
        self.reality=RealityCore(); self.constitution=BrainConstitution(); self.evidence=EvidenceStore(str(self.root/"evidence.db")); self.verification=VerificationCore(self.evidence,self.constitution); self.golden_gate=GoldenAcceptanceGate(self.evidence); self.missions={}
        # ASIC simulations and external telemetry use the supervisor's evidence journal.
        self.asic_resources=ASICResourceAdapter(evidence=self.evidence)

    def deliver_if_golden(self, job, criteria, *, expected_reality="SIMULATED", details=None):
        """Use the single mandatory guarded delivery path.

        Evidence producer labels are not cryptographic remote attestation and
        cannot independently prove remote executor identity or a real VM boot.
        """
        return self.transition(
            job, "deliver", status="completed", details=details,
            enforce_authority=False, golden_criteria=tuple(criteria),
            golden_expected_reality=expected_reality,
        )

    def _event(self,job_id,event,data=None):
        row={"ts":time.time(),"job_id":job_id,"event":event,"data":data or {}}
        with self.events_path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")

    def create(self,task,steps=None,budget=8):
        steps=steps or ["discover","plan","select_backend","execute","observe","verify","repair","recover","retry","deliver"]
        job=self.control.create(task,steps,max_attempts=self.max_cycles,budget=budget); job=self.control.start_attempt(job)
        self.missions[job["job_id"]]=Mission(job["job_id"],task,max_attempts=self.max_cycles)
        self._event(job["job_id"],"supervisor_created",{"steps":steps,"v13":"enabled"}); return job

    def execution_contract(self,job,action,executor="brain-supervisor",risk="LOW",expected_results=()):
        c=ExecutionContract(job["job_id"],job["job_id"],action,executor,expected_results=tuple(expected_results),risk=risk,
                             idempotency_key=f"{job['job_id']}:{action}:{job.get('attempts',0)}")
        c.validate(); self._event(job["job_id"],"execution_contract",c.as_dict()); return c

    def observe(self,job_id,key,value,source="supervisor",confidence=1.0,evidence_ids=()):
        mission=self.missions.get(job_id)
        if mission is not None:
            from .mission import MissionState
            if mission.state == MissionState.EXECUTING:
                mission.transition(MissionState.OBSERVING, reason="observation")
        mission=self.missions.get(job_id)
        recorded=self.evidence.append(job_id,key,{"value":value,"confidence":confidence,"evidence_ids":list(evidence_ids)},producer=source,mission_id=job_id,attempt=mission.attempts if mission else None,phase=mission.state.value if mission else None)
        if mission:
            mission.evidence_ids.append(recorded["evidence_id"])
        obs=self.reality.observe(Observation(key,value,source=source,confidence=confidence,evidence_ids=tuple(evidence_ids)+(recorded["evidence_id"],)))
        self._event(job_id,"observation",{"key":key,"kind":obs.kind.value,"confidence":obs.normalized_confidence(),"evidence_id":recorded["evidence_id"]}); return obs

    def transition(self,job,phase,status="running",details=None,enforce_authority=True,required_evidence_kind=None,golden_criteria=None,golden_expected_reality="SIMULATED"):
        allowed={"discover","plan","select_backend","execute","observe","verify","repair","recover","retry","deliver","blocked","completed","failed"}
        if phase not in allowed:raise ValueError("unknown_supervisor_phase")
        if phase=="deliver" and status=="completed":
            mission=self.missions.get(job["job_id"])
            if not golden_criteria:
                phase="blocked"; status="blocked"
                details={"completion_gate":"GOLDEN_ACCEPTANCE_CRITERIA_REQUIRED","reasons":["GOLDEN_ACCEPTANCE_CRITERIA_REQUIRED"]}
                self._event(job["job_id"],"golden_acceptance_gate",{"accepted":False,"status":"GOLDEN_ACCEPTANCE_CRITERIA_REQUIRED","reasons":["GOLDEN_ACCEPTANCE_CRITERIA_REQUIRED"]})
            else:
                try:
                    golden_result=self.golden_gate.evaluate(
                        job["job_id"], tuple(golden_criteria),
                        mission_id=job["job_id"],
                        attempt=mission.attempts if mission else None,
                        expected_reality=golden_expected_reality,
                    )
                    golden_data={
                        "accepted":golden_result.accepted,"status":golden_result.status,
                        "task_id":golden_result.task_id,"mission_id":golden_result.mission_id,
                        "attempt":golden_result.attempt,"reality_level":golden_result.reality_level,
                        "evidence_ids":list(golden_result.evidence_ids),
                        "criterion_results":list(golden_result.criterion_results),
                        "reasons":list(golden_result.reasons),
                    }
                except (TypeError, ValueError) as exc:
                    golden_result=None
                    golden_data={"accepted":False,"status":"INVALID_ACCEPTANCE_CONTRACT","reasons":[str(exc)]}
                self._event(job["job_id"],"golden_acceptance_gate",golden_data)
                if not golden_data["accepted"]:
                    phase="blocked"; status="blocked"
                    details={**(details or {}),"golden_acceptance":golden_data}
                else:
                    required_kind=required_evidence_kind or tuple(golden_criteria)[0].required_kind
                    result=self.verification.assert_success(
                        job["job_id"], required_kind=required_kind,
                        mission_id=job["job_id"],
                        attempt=mission.attempts if mission else None,
                    )
                    if not result.verified:
                        phase="blocked"; status="blocked"
                        details={"completion_gate":"RUNTIME_EVIDENCE_REQUIRED","reasons":list(result.reasons),"evidence_ids":list(result.evidence_ids),"golden_acceptance":golden_data}
                    else:
                        details={**(details or {}),"golden_acceptance":golden_data}
        if phase in {"execute","retry"} and enforce_authority:
            resource=self.resource_guard.sample()
            if resource.get("emergency"): details={"emergency":"RESOURCE_OVERLOAD","resource":resource,"previous_phase":phase}; phase="blocked"; status="blocked"
        mission=self.missions.get(job["job_id"])
        mission_map={"discover":"UNDERSTANDING","plan":"PLANNING","select_backend":"READY","execute":"EXECUTING","observe":"OBSERVING","verify":"VERIFYING","repair":"DIAGNOSING","recover":"RECOVERING","retry":"RETEST","deliver":"COMPLETED"}
        if mission and phase in mission_map:
            from .mission import MissionState
            target=MissionState[mission_map[phase]]
            if mission.state != target:
                mission.transition(target, reason=phase)
        if phase=="execute" and enforce_authority:
            self.execution_gateway.authorize("brain-internal-execution"); self.execution_contract(job,"execute")
        row=dict(job); row.update(phase=phase,status=status,updated_at=time.time(),details=details or {})
        idx={"discover":0,"plan":1,"select_backend":2,"execute":3,"observe":4,"verify":5,"repair":6,"recover":7,"retry":8,"deliver":9}.get(phase,row.get("step_index",0))
        if idx>=row.get("step_index",0):row=self.control.checkpoint(row,idx,row["details"])
        if status in {"blocked","failed","completed"}:row["status"]=status;self.control._append(self.control.jobs,row)
        if mission:
            row["mission_state"]=mission.state.value
            row["mission_attempts"]=mission.attempts
        self._event(row["job_id"],"phase",{"phase":phase,"status":status,"details":row["details"],"mission_state":mission.state.value if mission else None})
        return row

    def verify_evidence(self,job_id,required_kind=None):
        mission=self.missions.get(job_id)
        result=self.verification.verify(
            job_id,
            required_kind=required_kind,
            mission_id=job_id,
            attempt=mission.attempts if mission else None,
        )
        self._event(job_id,"evidence_verification",{"verified":result.verified,"evidence_ids":list(result.evidence_ids),"reasons":list(result.reasons)})
        return result

    def reason(self,evidence):
        decision=self.reasoner.next(evidence);self._event(evidence.get("job_id","unknown"),"reasoning_decision",self.reasoner.explain(decision));return decision

    def _completion_decision(self,verification):
        c=verification.get("completion_contract")
        if not c:return None
        gate=ProblemCompletionGate(CompletionContract(desired=c.get("desired",{}),invariants=c.get("invariants",{}),evidence_required=c.get("evidence_required",True)))
        return gate.decision(verification.get("verified_world",{}),verification.get("evidence",verification))

    def next_action(self,job,verification):
        completion=self._completion_decision(verification)
        acceptance_contract={
            "golden_criteria":verification.get("golden_criteria"),
            "golden_expected_reality":verification.get("golden_expected_reality","SIMULATED"),
        }
        if completion:
            if completion["action"]=="deliver":
                return {"action":"deliver","reason":"verified_problem_completion","completion":completion,**acceptance_contract}
            if job.get("attempts",0)>=job.get("max_attempts",self.max_cycles):return {"action":"blocked","reason":"attempt_limit_after_reality_check","completion":completion}
            return {"action":"treat","reason":"problem_not_complete","completion":completion}
        if verification.get("ok"):
            return {"action":"deliver","reason":"verification_contract_ok",**acceptance_contract}
        evidence_result=self.verify_evidence(job["job_id"],required_kind=verification.get("required_evidence_kind"))
        if evidence_result.verified:
            return {"action":"deliver","reason":"runtime_evidence_verified","evidence_ids":list(evidence_result.evidence_ids),**acceptance_contract}
        if job.get("attempts",0)>=job.get("max_attempts",self.max_cycles):return {"action":"blocked","reason":"attempt_limit"}
        return self.decide_repair(verification)

    def repair_and_retry(self,job,verification):
        action=self.next_action(job,verification)
        if action["action"]=="deliver":
            return self.transition(
                job,"deliver",status="completed",details=action,
                required_evidence_kind=verification.get("required_evidence_kind"),
                golden_criteria=action.get("golden_criteria"),
                golden_expected_reality=action.get("golden_expected_reality","SIMULATED"),
            )
        if action["action"]=="blocked":return self.transition(job,"blocked",status="blocked",details=action)
        repaired=self.transition(job,"repair",details=action)
        recovered=self.transition(repaired,"recover",details={"action":action["action"]})
        retried=self.control.start_attempt(recovered)
        self._event(retried["job_id"],"repair_retry_started",action)
        return self.transition(retried,"retry",details={"action":action["action"],"completion":action.get("completion")})

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
        for phase in ["discover","plan","select_backend","execute"]:job=self.transition(job,phase,details={"simulated":True},enforce_authority=False)
        verification={"ok":bool(verification_ok)}
        if verification_ok:
            self.observe(job["job_id"],"simulation_runtime_verified",True,source="simulation")
            job=self.transition(job,"observe",details={"simulated":True},enforce_authority=False)
            job=self.transition(job,"verify",details={"simulated":True},enforce_authority=False)
        else:
            job=self.transition(job,"repair",details=self.decide_repair(verification))
            job=self.transition(job,"recover",details={"bounded":True},enforce_authority=False)
            job=self.transition(job,"retry",details={"bounded":True},enforce_authority=False)
            job=self.transition(job,"execute",details={"retry":True},enforce_authority=False)
            self.observe(job["job_id"],"simulation_runtime_verified",True,source="simulation-repair")
            job=self.transition(job,"observe",details={"retry":True},enforce_authority=False)
            job=self.transition(job,"verify",details={"retry":True},enforce_authority=False)
        evidence_result=self.verify_evidence(job["job_id"],required_kind="simulation_runtime_verified")
        # Explicitly simulated fixture evidence exercises the acceptance path;
        # it is not proof of a real executor, device, VM, or remote operation.
        mission=self.missions.get(job["job_id"])
        runtime_item=self.evidence.append(
            job["job_id"],"simulation_runtime_verified",
            {"reality_level":"SIMULATED","simulation_harness":True},
            producer="simulation-harness",mission_id=job["job_id"],
            attempt=mission.attempts if mission else None,phase="VERIFYING",
        )
        self.evidence.append(
            job["job_id"],"independent_verification",
            {"verified":True,"reality_level":"SIMULATED",
             "verified_evidence_ids":[runtime_item["evidence_id"]],
             "criterion_ids":["simulation-runtime"]},
            producer="simulation-test-verifier",mission_id=job["job_id"],
            attempt=mission.attempts if mission else None,phase="VERIFYING",
        )
        from .golden_acceptance_gate import AcceptanceCriterion
        final="completed" if evidence_result.verified else "blocked"
        job=self.transition(
            job,"deliver",status="completed",details={"result":final},
            required_evidence_kind="simulation_runtime_verified",
            golden_criteria=(AcceptanceCriterion("simulation-runtime","simulation_runtime_verified"),),
            golden_expected_reality="SIMULATED",
        )
        self.snapshot(job,{"verified":evidence_result.verified,"result":job["status"]});return job

if __name__=="__main__":print(json.dumps(BrainSupervisor().run_simulation("supervisor_smoke_test"),indent=2))
