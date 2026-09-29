"""Human-like capability benchmark for Brain Cloud.

This is an evidence-first benchmark. It never assigns a capability score
without an executable test result. The 14 dimensions are intentionally
separate so the aggregate can be audited.
"""

from dataclasses import dataclass


TEST_WEIGHT_PERCENT = 0.02
TARGET_TESTS = 5000
TOTAL_BENCHMARK_PERCENT = TEST_WEIGHT_PERCENT * TARGET_TESTS

DIMENSIONS = (
    "reasoning",
    "planning",
    "learning",
    "memory",
    "generalization",
    "ambiguity",
    "self_correction",
    "tool_use",
    "autonomy",
    "failure_recovery",
    "language",
    "self_verification",
    "multi_agent_coordination",
    "safety",
    "goal_decomposition",
    "causal_reasoning",
    "counterfactual_reasoning",
    "long_horizon_execution",
    "context_switching",
    "working_memory",
    "knowledge_retrieval",
    "information_synthesis",
    "source_criticism",
    "uncertainty_calibration",
    "hypothesis_testing",
    "error_localization",
    "debugging",
    "code_generation",
    "code_review",
    "system_design",
    "api_integration",
    "data_analysis",
    "multimodal_understanding",
    "visual_reasoning",
    "audio_reasoning",
    "temporal_reasoning",
    "spatial_reasoning",
    "resource_management",
    "prioritization",
    "decision_traceability",
    "security_awareness",
    "permission_handling",
    "privacy_protection",
    "adversarial_robustness",
    "reproducibility",
    "observability",
    "rollback_recovery",
    "continuous_improvement",
    "human_collaboration",
    "novel_task_adaptation",
)


@dataclass(frozen=True)
class Evidence:
    dimension: str
    status: str
    evidence: str


def score(evidence: list[Evidence]) -> float:
    """Return a percentage only from explicit PASS/PARTIAL evidence.

    PASS=1, PARTIAL=0.5, anything else=0. This is a benchmark score,
    not a claim about consciousness, intelligence, or human equivalence.
    """
    weights = {"PASS": 1.0, "PARTIAL": 0.5}
    total = sum(weights.get(item.status.upper(), 0.0) for item in evidence)
    return round(TEST_WEIGHT_PERCENT * total, 2)


def validate_dimensions(evidence: list[Evidence]) -> None:
    unknown = {item.dimension for item in evidence} - set(DIMENSIONS)
    if unknown:
        raise ValueError(f"unknown benchmark dimensions: {sorted(unknown)}")


def benchmark_plan() -> dict[str, int]:
    base, remainder = divmod(TARGET_TESTS, len(DIMENSIONS))
    return {name: base + (1 if i < remainder else 0) for i, name in enumerate(DIMENSIONS)}


def validate_plan() -> None:
    plan = benchmark_plan()
    if sum(plan.values()) != TARGET_TESTS:
        raise AssertionError('benchmark plan does not total 5000 tests')
    if any(value <= 0 for value in plan.values()):
        raise AssertionError('every capability must have executable tests')


def main() -> None:
    print("BRAIN_HUMAN_LIKE_BENCHMARK=5000_TESTS")
    print(f"BRAIN_HUMAN_LIKE_TEST_WEIGHT_PERCENT={TEST_WEIGHT_PERCENT}")
    print(f"BRAIN_HUMAN_LIKE_TARGET_PERCENT={TOTAL_BENCHMARK_PERCENT}")
    print("BRAIN_HUMAN_LIKE_SCORE=UNMEASURED")
    print("BRAIN_HUMAN_LIKE_NOTE=No score is claimed without executable evidence.")


if __name__ == "__main__":
    main()
