from .evolution import AdaptiveGoalManager, ResearchMemory, EngineeringLoop, MultiAgentBus, SelfModel, EvolutionRegistry


class NextGenerationBrain:
    """Composition layer for the post-V1000 roadmap."""

    def __init__(self):
        self.goals = AdaptiveGoalManager()
        self.research = ResearchMemory()
        self.engineering = EngineeringLoop()
        self.agents = MultiAgentBus()
        self.self_model = SelfModel()
        self.registry = EvolutionRegistry()

    def bootstrap(self):
        for version in ("V1001", "V1100", "V1200", "V1300", "V1400",
                        "V1500", "V1600", "V1700", "V1800", "V1900", "V2000"):
            self.registry.advance(version)
        return self.registry.status()
