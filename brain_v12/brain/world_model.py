class WorldModel:
    def __init__(self): self.facts={}; self.predictions={}
    def set_fact(self,key,value,source="unknown",confidence=.5): self.facts[key]={"value":value,"source":source,"confidence":confidence}; return self.facts[key]
    def predict(self,key,expected,confidence=.5): self.predictions[key]={"expected":expected,"confidence":confidence}; return self.predictions[key]
    def observe(self,key,actual):
        p=self.predictions.get(key); expected=p["expected"] if p else None; match=p is not None and expected==actual
        return {"key":key,"actual":actual,"expected":expected,"match":match,"status":"SUCCESS" if match else ("UNKNOWN" if not p else "FAILED")}
    def snapshot(self): return {"facts":self.facts,"predictions":self.predictions}
