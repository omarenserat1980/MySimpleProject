from .decision_engine import DecisionEngine
from .event_bus import EventBus
from .permissions import PermissionGate
from .task_engine import TaskEngine
from .world_model import WorldModel
class CognitiveLoop:
    def __init__(self,store):
        self.store=store; self.events=EventBus(store); self.decisions=DecisionEngine(); self.permissions=PermissionGate(); self.tasks=TaskEngine(); self.world=WorldModel()
    def run(self,goal):
        self.events.publish("PERCEIVE",{"goal":goal}); self.events.publish("UNDERSTAND",{"goal":goal})
        options=self.decisions.generate(goal); decision=self.decisions.choose(goal,options,self.permissions.grants)
        self.events.publish("DECISION_MADE",decision)
        return {"goal":goal,"options":options,"decision":decision,"world":self.world.snapshot(),"tasks":self.tasks.snapshot()}
