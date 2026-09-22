class SalienceSystem:
    def __init__(self, weights=None):
        self.weights = weights or {"novelty":1.0,"prediction_error":1.0,"goal_relevance":1.0,"threat":1.0,"reward":1.0,"history":0.5}
        self.history = {}

    def score(self, observation, prediction_error=0.0, goal_relevance=0.0, threat=0.0, reward=0.0):
        key = observation.get("position", "unknown")
        novelty = 1.0 / (1.0 + self.history.get(key, 0))
        score = (self.weights["novelty"]*novelty + self.weights["prediction_error"]*prediction_error +
                 self.weights["goal_relevance"]*goal_relevance + self.weights["threat"]*threat +
                 self.weights["reward"]*reward + self.weights["history"]*(1.0-novelty))
        self.history[key] = self.history.get(key, 0) + 1
        return max(0.0, min(1.0, score / 5.5))

class ArousalSystem:
    def __init__(self): self.arousal = 0.5
    def update(self, salience, prediction_error, reward=0.0):
        self.arousal = max(0.0, min(1.0, 0.5*self.arousal + 0.3*salience + 0.2*min(1.0, abs(prediction_error)+abs(reward)/10)))
        return self.arousal
    def modulation(self):
        a = self.arousal
        return {"attention_gain":0.5+0.5*a,"learning_rate":0.05+0.25*a,"action_threshold":0.8-0.4*a,"exploration_rate":0.5*(1-a)}
