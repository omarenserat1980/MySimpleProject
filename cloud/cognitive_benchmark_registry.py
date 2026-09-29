"""Evidence-first external benchmark registry for Brain Cloud."""
from dataclasses import dataclass
from enum import StrEnum

class BenchmarkStatus(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    READY = "READY"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    name: str
    capability: str
    protocol: str
    official_source: str
    local_entrypoint: str
    requires_external_eval: bool = False

BENCHMARKS = (
    BenchmarkSpec("arc_agi_2", "ARC-AGI-2", "fluid reasoning", "Official ARC benchmarking harness; private evaluation stays external.", "arcprize.org", "ARC_AGI_2_RUNNER", True),
    BenchmarkSpec("arc_agi_3", "ARC-AGI-3", "interactive adaptation", "Official SDK and benchmarking harness; official private scoring stays external.", "arcprize.org", "ARC_AGI_3_RUNNER", True),
    BenchmarkSpec("hle", "Humanity's Last Exam", "expert knowledge reasoning", "Versioned official dataset/evaluation with provenance.", "lastexam.ai", "HLE_RUNNER"),
    BenchmarkSpec("gpqa_diamond", "GPQA Diamond", "graduate science reasoning", "Versioned dataset/evaluation with provenance.", "github.com/idavidrein/gpqa", "GPQA_RUNNER"),
    BenchmarkSpec("swe_bench_verified", "SWE-bench Verified", "software engineering", "Official test-based repository evaluation.", "swebench.com/verified", "SWEBENCH_VERIFIED_RUNNER"),
    BenchmarkSpec("osworld", "OSWorld", "computer use", "Official desktop/browser environment evaluator.", "os-world.github.io", "OSWORLD_RUNNER"),
    BenchmarkSpec("mmlu_pro", "MMLU-Pro", "general knowledge reasoning", "Versioned dataset/evaluation with provenance.", "huggingface.co", "MMLU_PRO_RUNNER"),
)

def get_benchmarks() -> tuple[BenchmarkSpec, ...]:
    return BENCHMARKS

def get(key: str) -> BenchmarkSpec:
    for item in BENCHMARKS:
        if item.key == key:
            return item
    raise KeyError(key)
