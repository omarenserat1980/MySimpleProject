class ThalamicRouter:
    ROUTES = {"visual":"sensory","audio":"sensory","body":"somatosensory","memory":"hippocampus","goal":"executive","high_salience":"workspace"}
    def route(self, event_type, payload, salience=0.0):
        destination = "workspace" if salience >= 0.75 else self.ROUTES.get(event_type, "association")
        return {"source":"thalamus","destination":destination,"payload":payload,"salience":salience}

class AssociationCortex:
    def __init__(self): self.concepts = {}
    def integrate(self, observation, memories, routed):
        key = (observation.get("position"), observation.get("goal"))
        self.concepts[key] = self.concepts.get(key, 0) + 1
        return {"context":key,"memory_count":len(memories),"activation":self.concepts[key],"routed_to":routed["destination"]}

class GlobalWorkspace:
    def __init__(self): self.current = None
    def broadcast(self, content):
        self.current = content
        return {"workspace":content}
