from .events import BrainEvent, EventBus
from .memory import HippocampalMemory
from .predictor import CerebellarPredictor
from .control import BasalGangliaSelector, InhibitoryController
from .modulation import SalienceSystem, ArousalSystem
from .routing import ThalamicRouter, AssociationCortex, GlobalWorkspace

class BrainCoreV2:
    def __init__(self, world):
        self.world=world; self.bus=EventBus(); self.memory=HippocampalMemory(); self.cerebellum=CerebellarPredictor()
        self.basal_ganglia=BasalGangliaSelector(); self.inhibition=InhibitoryController()
        self.salience=SalienceSystem(); self.arousal=ArousalSystem(); self.thalamus=ThalamicRouter()
        self.association=AssociationCortex(); self.workspace=GlobalWorkspace()
        self.total_error=0.0; self.steps=0; self.self_state={"goal":world.state.goal,"confidence":0.0,"prediction_error":0.0}
    def deliberate(self):
        obs=self.world.observe(); routed=self.thalamus.route("body",obs,0.0)
        memories=self.memory.recall(obs["position"]); assoc=self.association.integrate(obs,memories,routed)
        candidates=[]
        for action in self.world.ACTIONS:
            prediction=self.cerebellum.predict(obs,action)
            goal_alignment=1.0 if prediction.get("to")==obs["goal"] else (0.2 if prediction.get("to",0)>obs["position"] else -0.1)
            value=self.basal_ganglia.score(action,obs,prediction,goal_alignment)
            candidates.append({"action":action,"prediction":prediction,"value":value})
        selected=self.basal_ganglia.select(candidates)
        uncertainty=1.0-float(selected["prediction"].get("confidence",0)) if selected else 1.0
        risk=float(selected["prediction"].get("risk",0)) if selected else 1.0
        sal=self.salience.score(obs,self.self_state.get("prediction_error",0),1.0 if obs["position"]<obs["goal"] else 0.0,risk,0.0)
        arousal=self.arousal.update(sal,self.self_state.get("prediction_error",0))
        gate=self.inhibition.gate(selected,uncertainty,risk)
        decision={"observation":obs,"association":assoc,"candidates":candidates,"selected":selected,"gate":gate,"salience":sal,"arousal":arousal,"modulation":self.arousal.modulation()}
        self.workspace.broadcast(decision); return decision
    def step(self):
        decision=self.deliberate(); self.bus.publish(BrainEvent("executive","motor","DECISION",decision))
        if not decision["gate"]["commit"]: return {"status":"INHIBITED",**decision}
        obs=decision["observation"]; action=decision["selected"]["action"]; predicted=decision["selected"]["prediction"]
        outcome=self.world.step(action); error=self.cerebellum.learn(obs,action,outcome); self.memory.encode(obs,action,outcome)
        self.total_error+=error; self.steps+=1; self.self_state.update({"prediction_error":error,"confidence":predicted.get("confidence",0)})
        self.bus.publish(BrainEvent("world","learning","PREDICTION_ERROR",{"error":error,"outcome":outcome}))
        return {"status":"ACTED","action":action,"prediction":predicted,"outcome":outcome,"prediction_error":error,"self_state":dict(self.self_state)}
    def run(self,steps=20):
        history=[]
        for _ in range(steps):
            result=self.step(); history.append(result)
            if result.get("outcome",{}).get("reached"): break
        return {"steps":len(history),"total_prediction_error":self.total_error,"history":history,"self_state":self.self_state}
