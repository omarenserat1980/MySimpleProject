from dataclasses import dataclass, asdict
@dataclass
class Candidate:
    id:str; action:str; expected:str; risk:str="low"; requirements:list[str]|None=None; reversible:bool=True; evidence:list[str]|None=None; confidence:float=.5
    def __post_init__(self):
        self.requirements=self.requirements or []; self.evidence=self.evidence or []
class DecisionEngine:
    def __init__(self): self.history=[]
    def generate(self,goal):
        return [asdict(Candidate("observe","جمع معلومات إضافية","بيانات أوضح","low",["information"],True,["goal"],.70)),
                asdict(Candidate("plan","بناء خطة متعددة الخطوات","خطة قابلة للتحقق","low",["planning"],True,["goal"],.75)),
                asdict(Candidate("act","تنفيذ خطوة آمنة قابلة للعكس","تقدم قابل للتحقق","medium",["permission"],True,["goal"],.60))]
    def choose(self,goal,options,permissions=None):
        permissions=permissions or set(); ranked=[]
        for o in options:
            blocked=any(r not in permissions for r in o.get("requirements",[]) if r=="permission")
            score=float(o.get("confidence",.5))-(.35 if o.get("risk")=="high" else 0)-(.15 if not o.get("reversible",True) else 0)
            if blocked: score=-1
            ranked.append((score,o,blocked))
        ranked.sort(key=lambda x:x[0],reverse=True)
        result={"status":"WAITING_APPROVAL","goal":goal,"options":options,"reason":"permission_required"} if not ranked or ranked[0][2] else {"status":"DECIDED","goal":goal,"selected":ranked[0][1],"score":round(ranked[0][0],3),"reason":"traceable_heuristic","alternatives":[x[1] for x in ranked[1:]]}
        self.history.append(result); return result
