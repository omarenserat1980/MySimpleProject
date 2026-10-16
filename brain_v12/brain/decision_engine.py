from dataclasses import dataclass, asdict
import json
import math
from .memory import MemoryStore

@dataclass
class Candidate:
    id:str
    action:str
    expected:str
    risk:str="low"
    requirements:list[str]|None=None
    reversible:bool=True
    evidence:list[str]|None=None
    confidence:float=.5
    tool_id:str|None=None
    def __post_init__(self):
        self.requirements=self.requirements or []
        self.evidence=self.evidence or []

class DecisionEngine:
    def __init__(self):
        self.history=[]

    def generate(self,goal,memories=None):
        text=(goal or "").lower()
        code=any(x in text for x in ("كود","برمج","ملف","github","github","code","تطوير","إصلاح"))
        device=any(x in text for x in ("termux","redmi","هاتف","جهاز","موبايل","جوال","android","device","agent"))
        memory=any(x in text for x in ("ذاكرة","تذكر","memory","سجل"))
        options=[
            asdict(Candidate("observe","قراءة وفهم الحالة","بيانات قابلة للتحقق","low",[],True,["goal"],.82,
                             "memory.read" if memory else "state.read")),
            asdict(Candidate("plan","بناء خطة متعددة الخطوات","خطة قابلة للتحقق","low",[],True,["goal"],.80,"tasks.create")),
        ]
        if device:
            options.insert(0,asdict(Candidate("device","تنفيذ مهمة آمنة على الجهاز","نتيجة موثقة من Termux","medium",["device_agent"],True,["goal","device_result"],.92,"device.enqueue")))
        if code:
            options.insert(0,asdict(Candidate("inspect_code","فحص الكود المستهدف","صورة فعلية عن الكود الحالي","low",[],True,["goal","code"],.88,"code.inspect")))
            options.append(asdict(Candidate("verify_code","التحقق من الكود","نتيجة اختبار/تحقق موثقة","low",[],True,["code"],.84,"code.verify")))
            options.append(asdict(Candidate("apply_code","تطبيق تحسين برمجي","تغيير قابل للتراجع مع تحقق","high",["developer_approval"],True,["code","approval"],.65,"code.apply")))
        options.append(asdict(Candidate("act","تنفيذ خطوة حساسة","نتيجة خارجية قابلة للتحقق","high",["agent_approval"],True,["goal","approval"],.55,"agent.execute")))
        memory_keys = [str(m.get("key")) for m in (memories or []) if m.get("key")]
        for option in options:
            option["memory_context_keys"] = memory_keys[:12]
            if memory_keys:
                option["evidence"] = list(option.get("evidence") or []) + [f"memory:{key}" for key in memory_keys[:3]]
        return options

    @staticmethod
    def _has_verified_similar_success(goal, action, memories):
        goal_terms = MemoryStore._memory_terms(goal)
        if len(goal_terms) < 2:
            return False
        for memory in memories or []:
            if not str(memory.get("key", "")).startswith("cognitive.run."):
                continue
            try:
                lesson = json.loads(memory.get("value", "{}"))
            except (TypeError, ValueError):
                continue
            if (
                lesson.get("verified") is not True
                or lesson.get("goal_verified") is not True
                or lesson.get("verification_status") != "GOAL_VERIFIED"
                or lesson.get("outcome") != "VERIFIED_SUCCESS"
            ):
                continue
            if lesson.get("action") != action:
                continue
            prior_terms = MemoryStore._memory_terms(lesson.get("goal", ""))
            if len(goal_terms & prior_terms) >= 2:
                return True
        return False

    @staticmethod
    def _safe_confidence(value):
        try:
            confidence = float(value)
        except (TypeError, ValueError, OverflowError):
            return 0.5
        if not math.isfinite(confidence):
            return 0.5
        return min(1.0, max(0.0, confidence))

    @staticmethod
    def _safe_risk(value):
        risk = str(value or "").strip().lower()
        # Unknown/malformed risk labels must never silently become low risk.
        return risk if risk in {"low", "medium", "high"} else "high"

    def choose(self,goal,options,permissions=None,memories=None,approved_actions=None):
        permissions=set(permissions or [])
        approved_actions=set(approved_actions or [])
        eligible=[]
        blocked_options=[]
        for original in options:
            # Return decision annotations on copies; callers' candidate objects remain unchanged.
            o=dict(original)
            risk=self._safe_risk(o.get("risk", "low"))
            o["risk"]=risk
            req=o.get("requirements",[])
            if not isinstance(req, (list, tuple, set)):
                req=[]
            missing=[r for r in req if r not in permissions]
            explicit_approval_required = risk=="high" and o.get("id") not in approved_actions
            blocked=bool(missing) or explicit_approval_required
            base_score=self._safe_confidence(o.get("confidence",.5))
            risk_penalty=.30 if risk=="high" else (.10 if risk=="medium" else 0.0)
            reversibility_penalty=.15 if not o.get("reversible",True) else 0.0
            permission_penalty=.50 if missing else 0.0
            approval_penalty=.20 if explicit_approval_required else 0.0
            score=base_score-risk_penalty-reversibility_penalty-permission_penalty-approval_penalty
            learned_support=self._has_verified_similar_success(goal,o.get("id",""),memories)
            memory_tiebreaker=.02 if learned_support else 0.0
            score+=memory_tiebreaker
            o["learned_memory_support"]=learned_support
            o["decision_score"]=round(score,3)
            o["decision_score_breakdown"]={
                "base_confidence":round(base_score,3),
                "risk_penalty":risk_penalty,
                "irreversibility_penalty":reversibility_penalty,
                "missing_permission_penalty":permission_penalty,
                "approval_penalty":approval_penalty,
                "verified_memory_tiebreaker":memory_tiebreaker,
            }
            item={"score":score,"option":o,"missing_permissions":missing,
                  "approval_required":explicit_approval_required}
            if blocked:
                blocked_options.append(item)
            else:
                eligible.append(item)

        eligible.sort(key=lambda x:x["score"],reverse=True)
        blocked_options.sort(key=lambda x:x["score"],reverse=True)
        approval_summary=[
            {"id":item["option"].get("id"),"action":item["option"].get("action"),
             "missing_permissions":item["missing_permissions"],
             "approval_required":item["approval_required"],"score":round(item["score"],3)}
            for item in blocked_options
        ]

        if eligible:
            best=eligible[0]
            result={
                "status":"DECIDED",
                "goal":goal,
                "selected":best["option"],
                "score":round(best["score"],3),
                "reason":"highest_scoring_eligible_option",
                "alternatives":[item["option"] for item in eligible[1:]],
                "approval_required_options":approval_summary,
            }
        elif blocked_options:
            best=blocked_options[0]
            status="WAITING_PERMISSION" if best["missing_permissions"] else "WAITING_APPROVAL"
            result={
                "status":status,
                "goal":goal,
                "selected":best["option"],
                "score":round(best["score"],3),
                "reason":"required_permission" if best["missing_permissions"] else "explicit_approval_required",
                "missing_permissions":best["missing_permissions"],
                "approval_required":best["approval_required"],
                "alternatives":[],
                "approval_required_options":approval_summary,
            }
        else:
            result={"status":"NO_OPTIONS","goal":goal,"approval_required_options":[]}
        self.history.append(result)
        return result
