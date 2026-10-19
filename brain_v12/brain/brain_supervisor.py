"""Brain Supervisor: bounded autonomous orchestration over the existing Control Plane."""
from __future__ import annotations
import hashlib, json, os, time
from dataclasses import asdict, is_dataclass
from enum import Enum
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
from .multi_agent_collaboration import CollaborationCoordinator, TaskEnvelope
from ..asic.unit_001.sqlite_evidence_store import ExperimentMemory
from ..self_healing.problem_completion_gate import CompletionContract, ProblemCompletionGate
from ..self_healing.emergency_resource_guard import EmergencyResourceGuard

SAFE_EXTERNAL_ACTIONS={"submit_application","publish_external","move_money","withdraw"}

def _event_json_default(value):
    """Serialize structured values included in durable supervisor event records."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

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
        self.experiment_memory=ExperimentMemory(self.root/"experiment_memory.sqlite3")
        try:
            self.experiment_memory.init()
        except Exception as exc:
            self._event("supervisor","experiment_memory_init_failed",{"error_type":type(exc).__name__})
        self.max_cycles=max(1,min(int(max_cycles),5))
        self.control=ControlPlane(str(self.root/"control_plane")); self.reasoner=AutonomousReasoner()
        self.execution_gateway=execution_gateway or BrainExecutionGateway(); self.resource_guard=EmergencyResourceGuard()
        self.reality=RealityCore(); self.constitution=BrainConstitution(); self.evidence=EvidenceStore(str(self.root/"evidence.db")); self.verification=VerificationCore(self.evidence,self.constitution); self.golden_gate=GoldenAcceptanceGate(self.evidence); self.missions={}
        # ASIC simulations and external telemetry use the supervisor's evidence journal.
        self.asic_resources=ASICResourceAdapter(evidence=self.evidence)
        # Collaboration policy is subordinate to this single authoritative supervisor.
        self.collaboration=CollaborationCoordinator()

    def create_collaboration_task(self, envelope: TaskEnvelope):
        """Create a bounded role task under the authoritative Brain supervisor."""
        task = self.collaboration.create_task(envelope)
        self._event(
            envelope.task_id,
            "collaboration_task_created",
            {"role": envelope.role.value, "branch": envelope.branch,
             "base_commit": envelope.base_commit, "allowed_paths": list(envelope.allowed_paths),
             "acceptance_criteria": list(envelope.acceptance_criteria)},
        )
        return task

    def collaboration_record(self, task_id: str):
        """Export a machine-readable collaboration snapshot and append its status to Brain audit events."""
        record = self.collaboration.export_record(task_id)
        self._event(
            task_id, "collaboration_snapshot",
            {"state": record["state"], "attempt": record["attempt"],
             "head_commit": record["head_commit"], "reviewer_id": record["reviewer_id"],
             "evidence_count": len(record["evidence"])},
        )
        return record

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
        with self.events_path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False,default=_event_json_default)+"\n")

    @staticmethod
    def _task_subject(task):
        """Fingerprint task text so SQLite history can be matched without storing the prompt."""
        normalized=" ".join(str(task).split()).casefold()
        return "task-sha256:"+hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def task_history(self,task,limit=20):
        """Read prior safe task outcomes by fingerprint; raw task text is never stored in SQLite."""
        try:
            events=self.experiment_memory.list_events(subject=self._task_subject(task),limit=limit)
        except Exception as exc:
            self._event("supervisor","experiment_memory_read_failed",{"error_type":type(exc).__name__})
            return []
        return [{
            "event_type":event["event_type"],"status":event["status"],
            "occurred_at_utc":event["occurred_at_utc"],
            "job_id":event["measurements"].get("job_id"),
            "phase":event["measurements"].get("phase"),
            "mission_state":event["measurements"].get("mission_state"),
        } for event in events]

    def _remember_transition(self,job,phase,status,mission):
        """Persist a whitelist of orchestration metadata, never arbitrary task details."""
        try:
            self.experiment_memory.record({
                "project":"Electronic Brain",
                "subject":self._task_subject(job.get("task","")),
                "event_type":"supervisor_phase",
                "status":str(status or "running").upper(),
                "environment":{"runtime":"brain_supervisor"},
                "measurements":{
                    "job_id":str(job.get("job_id","")),
                    "phase":str(phase),
                    "mission_state":mission.state.value if mission else None,
                    "attempts":int(mission.attempts) if mission else int(job.get("attempts",0)),
                    "step_index":int(job.get("step_index",0)),
                },
                "evidence":[],
                "limitations":[
                    "Records orchestration metadata only; it is not independent execution evidence.",
                    "Does not prove physical hardware, mining, pool acceptance, or realized revenue.",
                ],
            })
        except Exception as exc:
            self._event(job.get("job_id","supervisor"),"experiment_memory_write_failed",{"error_type":type(exc).__name__})

    def create(self,task,steps=None,budget=8):
        steps=steps or ["discover","plan","select_backend","execute","observe","verify","repair","recover","retry","deliver"]
        job=self.control.create(task,steps,max_attempts=self.max_cycles,budget=budget); job=self.control.start_attempt(job)
        self.missions[job["job_id"]]=Mission(job["job_id"],task,max_attempts=self.max_cycles)
        self._event(job["job_id"],"supervisor_created",{"steps":steps,"v13":"enabled"})
        self._remember_transition(job,"created","created",self.missions[job["job_id"]])
        return job

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
        row_details=dict(details or {})
        if phase=="plan":
            prior=self.task_history(job.get("task",""),limit=50)
            prior=[item for item in prior if item.get("job_id")!=job.get("job_id")]
            # Keep only safe, bounded metadata and attach it before checkpointing so
            # the persisted job state and downstream planner can actually consume it.
            row_details["prior_task_history"]=prior
        row=dict(job); row.update(phase=phase,status=status,updated_at=time.time(),details=row_details)
        if phase=="plan":
            row["prior_task_history"]=row_details["prior_task_history"]
        idx={"discover":0,"plan":1,"select_backend":2,"execute":3,"observe":4,"verify":5,"repair":6,"recover":7,"retry":8,"deliver":9}.get(phase,row.get("step_index",0))
        if idx>=row.get("step_index",0):row=self.control.checkpoint(row,idx,row["details"])
        if status in {"blocked","failed","completed"}:row["status"]=status;self.control._append(self.control.jobs,row)
        if mission:
            row["mission_state"]=mission.state.value
            row["mission_attempts"]=mission.attempts
        self._event(row["job_id"],"phase",{"phase":phase,"status":status,"details":row["details"],"mission_state":mission.state.value if mission else None})
        self._remember_transition(row,phase,status,mission)
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

    def evaluate_pathway(self,pathway_id,evidence,expected_run_id=None,job_id=None):
        """Evaluate a declared cross-system pathway and persist its blocker trace."""
        from .pathway_engine import evaluate_pathway
        result=evaluate_pathway(pathway_id,evidence,expected_run_id=expected_run_id)
        self._event(job_id or "pathway-planner","pathway_evaluation",{
            "pathway":pathway_id,
            "status":result["status"],
            "next_gate":result["next_gate"],
            "blockers":result["blockers"],
            "expected_run_id":expected_run_id,
        })
        return result

    def reason(self,evidence):
        # Enrich reasoning input with prior safe history when the task identity is known.
        # Never infer execution success from history; the reasoner still requires current evidence.
        context=dict(evidence or {})
        job_id=str(context.get("job_id","unknown"))
        task=context.get("task")
        if not task and job_id != "unknown":
            task_record=next((item for item in self.control.jobs if str(item.get("job_id"))==job_id),None)
            if task_record:
                task=task_record.get("task")
        if task:
            prior=self.task_history(task,limit=50)
            context["prior_task_history"]=[
                item for item in prior if item.get("job_id") != job_id
            ]
        history=context.get("prior_task_history",[])
        decision=self.reasoner.next(context)
        if history:
            blocked_or_failed=sum(
                1 for item in history
                if str(item.get("status","")).upper() in {"BLOCKED","FAILED"}
            )
            decision.reason=(
                f"{decision.reason}; prior_task_history_events={len(history)};"
                f" prior_blocked_or_failed={blocked_or_failed}"
            )
        self._event(job_id,"reasoning_decision",{
            **self.reasoner.explain(decision),
            "prior_history_count":len(history),
            "prior_blocked_or_failed":sum(
                1 for item in history
                if str(item.get("status","")).upper() in {"BLOCKED","FAILED"}
            ),
        })
        return decision

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
