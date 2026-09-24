from dataclasses import dataclass, asdict

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

    def generate(self,goal):
        text=(goal or "").lower()
        code=any(x in text for x in ("كود","برمج","ملف","github","github","code","تطوير","إصلاح"))
        memory=any(x in text for x in ("ذاكرة","تذكر","memory","سجل"))
        options=[
            asdict(Candidate("observe","قراءة وفهم الحالة","بيانات قابلة للتحقق","low",[],True,["goal"],.82,
                             "memory.read" if memory else "state.read")),
            asdict(Candidate("plan","بناء خطة متعددة الخطوات","خطة قابلة للتحقق","low",[],True,["goal"],.80,"tasks.create")),
        ]
        if code:
            options.insert(0,asdict(Candidate("inspect_code","فحص الكود المستهدف","صورة فعلية عن الكود الحالي","low",[],True,["goal","code"],.88,"code.inspect")))
            options.append(asdict(Candidate("verify_code","التحقق من الكود","نتيجة اختبار/تحقق موثقة","low",[],True,["code"],.84,"code.verify")))
            options.append(asdict(Candidate("apply_code","تطبيق تحسين برمجي","تغيير قابل للتراجع مع تحقق","high",["developer_approval"],True,["code","approval"],.65,"code.apply")))
        options.append(asdict(Candidate("act","تنفيذ خطوة حساسة","نتيجة خارجية قابلة للتحقق","high",["agent_approval"],True,["goal","approval"],.55,"agent.execute")))
        return options

    def choose(self,goal,options,permissions=None):
        permissions=permissions or set()
        ranked=[]
        for o in options:
            req=o.get("requirements",[])
            missing=[r for r in req if r not in permissions]
            blocked=bool(missing)
            score=float(o.get("confidence",.5))
            if o.get("risk")=="high": score-=.30
            if not o.get("reversible",True): score-=.15
            if blocked: score-=.50
            ranked.append((score,o,blocked,missing))
        ranked.sort(key=lambda x:x[0],reverse=True)
        if not ranked:
            result={"status":"NO_OPTIONS","goal":goal}
        else:
            score,selected,blocked,missing=ranked[0]
            if blocked and selected.get("risk")=="high":
                result={"status":"WAITING_APPROVAL","goal":goal,"selected":selected,"score":round(score,3),
                        "reason":"required_permission","missing_permissions":missing,
                        "alternatives":[x[1] for x in ranked[1:]]}
            else:
                result={"status":"DECIDED","goal":goal,"selected":selected,"score":round(score,3),
                        "reason":"tool_aware_heuristic","alternatives":[x[1] for x in ranked[1:]]}
        self.history.append(result)
        return result
