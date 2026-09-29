"""Evidence-first cognitive benchmark for Brain Cloud.

The benchmark combines public reference families with Brain-specific tests.
It is a measurement framework, not a claim of human equivalence or age.
External benchmark results are only accepted when their evaluation protocol
and provenance are recorded.
"""

from dataclasses import dataclass


TEST_WEIGHT_PERCENT = 0.02
TARGET_TESTS = 5000
TOTAL_BENCHMARK_PERCENT = TEST_WEIGHT_PERCENT * TARGET_TESTS

REFERENCE_BENCHMARKS = {
    'fluid_reasoning': 'ARC-AGI-2',
    'interactive_adaptation': 'ARC-AGI-3',
    'expert_knowledge_reasoning': "Humanity's Last Exam",
    'graduate_science_reasoning': 'GPQA Diamond',
    'software_engineering': 'SWE-bench Verified',
    'computer_use': 'OSWorld',
    'general_knowledge_reasoning': 'MMLU-Pro',
}

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
    """Return earned percentage from at most the 5,000-test budget."""
    validate_dimensions(evidence)
    if len(evidence) > TARGET_TESTS:
        raise ValueError("evidence exceeds the 5000-test benchmark budget")
    weights = {"PASS": 1.0, "PARTIAL": 0.5}
    earned = sum(weights.get(item.status.upper(), 0.0) for item in evidence)
    return round(TEST_WEIGHT_PERCENT * earned, 2)


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
