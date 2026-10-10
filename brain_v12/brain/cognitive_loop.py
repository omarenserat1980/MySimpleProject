from .decision_engine import DecisionEngine
from .event_bus import EventBus
from .permissions import PermissionGate
from .task_engine import TaskEngine
from .world_model import WorldModel
from .quranic_reasoning_paths import select_reasoning_path
from uuid import uuid4
import hashlib
import json

class CognitiveLoop:
    """Traceable V12 cognitive pipeline. Exposes high-level state, never private chain-of-thought."""
    STAGES=["PERCEIVE","UNDERSTAND","MEMORY","ANALYZE","PLAN","DECIDE","EXECUTE","VERIFY","LEARN"]
    TOOL_CATALOG=[
        {"id":"memory.read","name":"قراءة الذاكرة","risk":"low","permission":None},
        {"id":"state.read","name":"قراءة حالة العقل","risk":"low","permission":None},
        {"id":"tasks.create","name":"إنشاء مهمة","risk":"low","permission":None},
        {"id":"tasks.complete","name":"إكمال مهمة","risk":"low","permission":None},
        {"id":"code.inspect","name":"فحص الكود","risk":"low","permission":"developer"},
        {"id":"code.verify","name":"التحقق من الكود","risk":"low","permission":"developer"},
        {"id":"device.enqueue","name":"إرسال مهمة إلى Termux","risk":"medium","permission":"device_agent"},
        {"id":"code.apply","name":"تعديل الكود","risk":"high","permission":"developer_approval"},
        {"id":"agent.execute","name":"تنفيذ معزول","risk":"high","permission":"agent_approval"},
    ]

    def __init__(self,store):
        self.store=store
        self.events=EventBus(store)
        self.decisions=DecisionEngine()
        self.permissions=PermissionGate()
        self.tasks=TaskEngine()
        self.world=WorldModel()
        self.code_tool=None

    def _state(self,stage,status="RUNNING",**extra):
        current=self.store.state()
        current.update({
            "status":status,
            "cognitive_stage":stage,
            "cognitive_stage_index":self.STAGES.index(stage) if stage in self.STAGES else -1,
            "cognitive_total":len(self.STAGES),
            "cognitive_trace":extra,
        })
        self.store.set_state(current)
        return current

    def tool_catalog(self):
        return self.TOOL_CATALOG

    def execute_tool(self,tool_id,params=None,approved=False,_retry=False):
        params=params or {}
        item=next((x for x in self.TOOL_CATALOG if x["id"]==tool_id),None)
        self.events.publish("TOOL_SELECTED",{"tool":tool_id,"approved":approved})
        if not item:
            result={"ok":False,"status":"UNKNOWN_TOOL","tool":tool_id}
        elif item["permission"] and (item["permission"] not in self.permissions.grants or (item["risk"]=="high" and not approved)):
            result={"ok":False,"status":"WAITING_PERMISSION","tool":tool_id,"permission":item["permission"]}
        elif tool_id=="memory.read":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.store.memories()[:int(params.get("limit",12))]}
        elif tool_id=="state.read":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.store.state()}
        elif tool_id=="tasks.create":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.tasks.create(str(params.get("title","مهمة جديدة")))}
        elif tool_id=="tasks.complete":
            result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.tasks.update(str(params.get("task_id")),"COMPLETED")}
        elif tool_id=="code.inspect":
            if not self.code_tool:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.code_tool.inspect(str(params.get("path","brain_v12/app.py")))}
        elif tool_id=="code.verify":
            if not self.code_tool:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                result={"ok":True,"status":"COMPLETED","tool":tool_id,"data":self.code_tool.verify(params.get("paths",[]))}
        elif tool_id=="device.enqueue":
            bridge = getattr(self, "device_bridge", None)
            if not bridge:
                result={"ok":False,"status":"UNAVAILABLE","tool":tool_id}
            else:
                queued=bridge.enqueue(str(params.get("task","status")), params.get("params",{}))
                if not queued.get("ok"):
                    result=queued
                else:
                    task_id=queued["task"]["task_id"]
                    completed=bridge.wait_result(task_id, float(params.get("timeout", 20)))
                    result={
                        "ok": bool(completed.get("ok")),
                        "status": completed.get("task",{}).get("status", completed.get("status", "RESULT_TIMEOUT")),
                        "tool": tool_id,
                        "task": queued["task"],
                        "result": completed.get("task",{}).get("result", {}),
                        "error": completed.get("task",{}).get("error", ""),
                    }
        else:
            result={"ok":False,"status":"DELEGATED","tool":tool_id,"reason":"الأداة تحتاج المسار المخصص لها."}
        self.events.publish("TOOL_RESULT",result)
        if not result.get("ok") and not _retry and item and item.get("risk")=="low":
            self.events.publish("TOOL_RETRY",{"tool":tool_id,"reason":"safe_tool_failure","attempt":2})
            return self.execute_tool(tool_id,params,approved,True)
        return result

    def run(self,goal):
        goal=(goal or "").strip()
        run_id=str(uuid4())
        self._state("PERCEIVE",goal=goal,run_id=run_id)
        self.events.publish("COGNITIVE_RUN_STARTED",{"run_id":run_id,"goal":goal})
        self.events.publish("PERCEIVE",{"goal":goal,"run_id":run_id})

        self._state("UNDERSTAND",goal=goal,run_id=run_id)
        self.events.publish("UNDERSTAND",{"goal":goal,"summary":"تحديد المطلوب والنتيجة المتوقعة","run_id":run_id})

        self._state("MEMORY",goal=goal,run_id=run_id)
        all_memories=self.store.memories()
        recall_fn=getattr(self.store,"recall_memories",None)
        memories=recall_fn(goal,limit=12) if callable(recall_fn) else all_memories[-12:]
        # Count durable run lessons across the full store, not only the recalled slice.
        prior_lessons=[m for m in all_memories if str(m.get("key","")).startswith("cognitive.run.")]
        reasoning_path=select_reasoning_path(goal,memories)
        decision_memories=list(memories)
        if reasoning_path:
            decision_memories.append({
                "key":reasoning_path["key"],
                "value":" ".join([reasoning_path["title"],reasoning_path["engineering_application"]," ".join(reasoning_path["stages"])])
            })
            self.events.publish("REASONING_PATH_SELECTED",{
                "key":reasoning_path["key"],
                "title":reasoning_path["title"],
                "stages":reasoning_path["stages"],
                "source_references":reasoning_path["source_references"],
                "interpretation_type":reasoning_path.get("interpretation_type","bounded_engineering_inference"),
                "run_id":run_id
            })
        self.events.publish("MEMORY_RECALL",{
            "count":len(memories),
            "prior_lesson_count":len(prior_lessons),
            "memory_keys":[str(m.get("key","")) for m in memories[:12]],
            "reasoning_path_key":reasoning_path.get("key") if reasoning_path else None,
            "run_id":run_id
        })

        self._state("ANALYZE",goal=goal,run_id=run_id)
        options=self.decisions.generate(goal,memories=decision_memories)
        self.events.publish("ANALYZE",{"options_count":len(options),"memory_context_count":len(decision_memories),"run_id":run_id})

        self._state("PLAN",goal=goal,run_id=run_id)
        plan_steps=reasoning_path["stages"] if reasoning_path else ["فهم الطلب","تقييم الخيارات","اختيار الخطوة الآمنة","التحقق"]
        self.events.publish("PLAN_CREATED",{"steps":plan_steps,"reasoning_path_key":reasoning_path.get("key") if reasoning_path else None,"run_id":run_id})

        self._state("DECIDE",goal=goal,run_id=run_id)
        decision=self.decisions.choose(goal,options,self.permissions.grants,memories=decision_memories)
        decision["run_id"]=run_id
        self.events.publish("DECISION_MADE",decision)

        selected=decision.get("selected",{})
        action=selected.get("id","observe") if isinstance(selected,dict) else "observe"

        self._state("EXECUTE",goal=goal,run_id=run_id)
        task_title=selected.get("action","تحليل الهدف") if isinstance(selected,dict) else "تحليل الهدف"
        task=self.tasks.create(task_title)
        self.tasks.update(task["id"],"RUNNING")
        self.events.publish("EXECUTION_STARTED",{"task_id":task["id"],"action":action,"title":task_title,"run_id":run_id})

        tool_id={"observe":"memory.read","plan":"tasks.create","inspect_code":"code.inspect","verify_code":"code.verify","device":"device.enqueue"}.get(action)
        tool_params = (
            {"title":task_title} if tool_id=="tasks.create"
            else {"path":"brain_v12/app.py"} if tool_id=="code.inspect"
            else {"task":"status","params":{}} if tool_id=="device.enqueue"
            else {}
        )
        tool_result=self.execute_tool(tool_id,tool_params) if tool_id else None
        device_success = bool(action == "device" and tool_result and tool_result.get("ok") and tool_result.get("status") == "COMPLETED" and isinstance(tool_result.get("result"), dict))
        if (action in {"observe","plan"} and tool_result and tool_result.get("ok")) or device_success:
            # TaskEngine enforces evidence-gated completion. Bind the evidence to
            # the exact tool result so a rejected completion cannot be reported as success.
            evidence_json=json.dumps(tool_result,sort_keys=True,ensure_ascii=False,default=str)
            evidence_sha=hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
            evidence_ref=f"cognitive://{run_id}/{tool_id or 'no-tool'}/{evidence_sha}"
            completion=self.tasks.update(task["id"],"COMPLETED",evidence_ref=evidence_ref)
            if completion.get("status") == "COMPLETED":
                execution={"status":"COMPLETED","action":action,"task_id":task["id"],"tool":tool_id,"tool_result":tool_result,"evidence_ref":evidence_ref,"result":"تم تنفيذ الخطوة الآمنة واستلام النتيجة.","run_id":run_id}
                self.events.publish("EXECUTION_COMPLETED",execution)
            else:
                execution={"status":"FAILED","action":action,"task_id":task["id"],"tool":tool_id,"tool_result":tool_result,"error":completion.get("error","TASK_COMPLETION_REJECTED"),"result":"رفض نظام المهام إكمال المهمة؛ لم يُعلن نجاحها.","run_id":run_id}
                self.events.publish("EXECUTION_FAILED",execution)
        else:
            self.tasks.update(task["id"],"PENDING")
            execution={"status":"WAITING_PERMISSION" if tool_result and tool_result.get("status")=="WAITING_PERMISSION" else "FAILED","action":action,"task_id":task["id"],"tool":tool_id,"tool_result":tool_result,"result":"لم تكتمل الخطوة.","run_id":run_id}
            self.events.publish("EXECUTION_WAITING_PERMISSION" if execution["status"]=="WAITING_PERMISSION" else "EXECUTION_FAILED",execution)

        self._state("VERIFY",goal=goal,run_id=run_id,task_id=task["id"])
        verified_task=next((x for x in self.tasks.snapshot()["tasks"] if x["id"]==task["id"]),None)
        verified = bool(
            verified_task
            and verified_task["status"] == "COMPLETED"
            and (action != "device" or device_success)
        )
        verification={
            "status":"VERIFIED" if verified else "PENDING",
            "task_status":verified_task["status"] if verified_task else "UNKNOWN",
            "evidence":"تم فحص حالة المهمة والنتيجة المستلمة من Termux." if action=="device" else "تم فحص حالة المهمة بعد التنفيذ الداخلي.",
            "result_verified":verified,
            "run_id":run_id
        }
        self.events.publish("VERIFIED",verification)

        self._state("LEARN",status="READY",goal=goal,run_id=run_id)
        outcome = "VERIFIED_SUCCESS" if verification.get("result_verified") else (
            "WAITING_PERMISSION" if execution.get("status")=="WAITING_PERMISSION" else "FAILED_OR_UNVERIFIED"
        )
        lesson={
            "run_id":run_id,
            "goal":goal,
            "action":action,
            "outcome":outcome,
            "execution_status":execution.get("status"),
            "verification_status":verification.get("status"),
            "verified":bool(verification.get("result_verified")),
        }
        # A unique key preserves history instead of overwriting the previous run.
        self.store.save_memory(
            f"cognitive.run.{run_id}",
            __import__("json").dumps(lesson,ensure_ascii=False,sort_keys=True)
        )
        self.events.publish("LEARNING_RECORDED",{"lesson":lesson,"run_id":run_id})

        return {
            "run_id":run_id,
            "goal":goal,
            "stages":self.STAGES,
            "stage_count":len(self.STAGES),
            "memory_count":len(memories),
            "prior_lesson_count":len(prior_lessons),
            "reasoning_path":({"key":reasoning_path["key"],"title":reasoning_path["title"],"source_references":reasoning_path["source_references"],"interpretation_type":reasoning_path.get("interpretation_type","bounded_engineering_inference")} if reasoning_path else None),
            "plan_steps":plan_steps,
            "options":options,
            "decision":decision,
            "execution":execution,
            "verification":verification,
            "learning":{"status":"RECORDED","lesson":lesson},
            "tool_result":tool_result,
            "world":self.world.snapshot(),
            "tasks":self.tasks.snapshot()
        }
