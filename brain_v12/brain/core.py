from .planner import options_for, choose

class BrainCore:
    def __init__(self,store):
        self.store=store

    def snapshot(self):
        return self.store.state()

    def think(self):
        goal=self.store.active_goal()
        if not goal:
            self.store.set_state({"status":"IDLE","reason":"NO_GOAL"})
            return {"status":"IDLE","reason":"NO_GOAL"}
        if goal["status"]=="PENDING":
            self.store.set_goal_status(goal["id"],"IN_PROGRESS")
        options=options_for(goal)
        selected=choose(goal,options)
        state={
            "status":"DECIDING",
            "goal_id":goal["id"],
            "current_goal":goal["text"],
            "options":options,
            "selected":selected,
            "prediction":selected["expected"],
            "prediction_error":None
        }
        self.store.set_state(state)
        self.store.event("DECISION",{"goal_id":goal["id"],"selected":selected})
        return state

    def observe(self,actual):
        state=self.store.state()
        if state.get("status") not in ("DECIDING","ACTING","OBSERVING"):
            return {"ok":False,"error":"NO_ACTIVE_CYCLE"}
        expected=state.get("prediction")
        error=0.0 if actual==expected else 1.0
        state.update({"status":"LEARNED","actual":actual,"prediction_error":error})
        self.store.set_state(state)
        self.store.event("FEEDBACK",{"expected":expected,"actual":actual,"prediction_error":error})
        if error==0 and state.get("goal_id"):
            self.store.set_goal_status(state["goal_id"],"DONE")
        return {"ok":True,"state":state}

    def learn(self,lesson):
        self.store.save_memory("lesson:last",lesson)
        self.store.event("LEARNING",{"lesson":lesson})
        return {"ok":True,"lesson":lesson}
