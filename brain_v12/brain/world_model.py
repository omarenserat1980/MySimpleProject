"""Small explicit world model: facts, assumptions, predictions and observations."""
class WorldModel:
    def __init__(self):
        self.facts = {}
        self.assumptions = {}
        self.predictions = {}

    def set_fact(self, key, value, source="unknown", confidence=0.5):
        self.facts[key] = {"value":value,"source":source,"confidence":confidence}
        return self.facts[key]

    def predict(self, key, expected, confidence=0.5):
        self.predictions[key] = {"expected":expected,"confidence":confidence}
        return self.predictions[key]

    def observe(self, key, actual):
        prediction = self.predictions.get(key)
        match = prediction is not None and prediction["expected"] == actual
        return {"key":key,"actual":actual,"expected":prediction["expected"] if prediction else None,
                "match":match,"status":"SUCCESS" if match else ("UNKNOWN" if not prediction else "FAILED")}

    def snapshot(self):
        return {"facts":self.facts,"assumptions":self.assumptions,"predictions":self.predictions}
