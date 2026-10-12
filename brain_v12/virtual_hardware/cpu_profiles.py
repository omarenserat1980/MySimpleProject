"""Selectable CPU reference profiles with explicit emulation-fidelity boundaries.

Real processor entries are reference configurations, not claims that this interpreter
implements their complete ISA or reproduces their microarchitecture.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INTEL_SDM = "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html"
AMD_APM = "https://docs.amd.com/v/u/en-US/40332_4.09_APM_PUB"
INTEL_I7_6700 = "https://www.intel.com/content/www/us/en/products/sku/88196/intel-core-i76700-processor-8m-cache-up-to-4-00-ghz.html"
AMD_RYZEN_5600 = "https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600.html"


@dataclass(frozen=True)
class CPUProfile:
    profile_id: str
    vendor: str
    model: str
    isa: str
    specification_urls: tuple[str, ...]
    specification_parameters: dict[str, Any]
    fidelity: str
    modeled_behaviors: tuple[str, ...]
    unsupported_features: tuple[str, ...]
    conformance_tests: tuple[str, ...]

    def describe(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "vendor": self.vendor,
            "model": self.model,
            "isa": self.isa,
            "specification_urls": list(self.specification_urls),
            "specification_parameters": dict(self.specification_parameters),
            "fidelity": self.fidelity,
            "modeled_behaviors": list(self.modeled_behaviors),
            "unsupported_features": list(self.unsupported_features),
            "conformance_tests": list(self.conformance_tests),
            "physical_performance_claim": False,
            "microarchitecture_simulation": "not_implemented",
        }


_COMMON_UNSUPPORTED = (
    "binary x86 instruction-byte decoding",
    "complete x86-64 instruction set",
    "AVX/AVX2/AVX-512 and SIMD execution",
    "x87 and IEEE floating-point execution",
    "page tables and virtual-address translation",
    "ring 0/1/2 execution and privileged instructions",
    "SMT thread scheduling",
    "branch prediction and speculative execution",
    "cycle-accurate pipeline and cache-coherence behavior",
    "physical performance equivalence",
)

CPU_PROFILES: dict[str, CPUProfile] = {
    "brain-x86-64-subset-v1": CPUProfile(
        profile_id="brain-x86-64-subset-v1",
        vendor="Electronic Brain",
        model="X86_64CPU tuple-instruction compatibility profile",
        isa="x86-64-inspired tuple ISA subset (not binary x86 decoding)",
        specification_urls=(INTEL_SDM, AMD_APM),
        specification_parameters={"register_width_bits": 64, "register_count": 16, "instruction_encoding": "symbolic tuples"},
        fidelity="functional_subset",
        modeled_behaviors=("symbolic NOP/HLT/MOVI/ADD/SUB/XOR/CMP/JMP/JZ/OUT", "64-bit integer wrap", "selected arithmetic flags"),
        unsupported_features=_COMMON_UNSUPPORTED,
        conformance_tests=("test_cpu_profile_metadata", "test_x86_subset_instruction_vectors", "test_x86_flags_and_overflow"),
    ),
    "intel-core-i7-6700": CPUProfile(
        profile_id="intel-core-i7-6700",
        vendor="Intel",
        model="Intel Core i7-6700 (Skylake desktop reference)",
        isa="Intel 64 / IA-32",
        specification_urls=(INTEL_I7_6700, INTEL_SDM),
        specification_parameters={
            "physical_cores": 4, "threads": 8, "base_clock_hz": 3_400_000_000,
            "max_turbo_clock_hz": 4_000_000_000, "l3_cache_bytes": 8_388_608,
            "tdp_watts": 65, "cache_note": "Intel lists 8 MB Intel Smart Cache; L1/L2 values not asserted here",
        },
        fidelity="functional_subset",
        modeled_behaviors=("the same explicitly listed symbolic x86-inspired subset", "reference metadata for profile selection"),
        unsupported_features=_COMMON_UNSUPPORTED + ("Intel Core i7-6700 pipeline/cache latency model",),
        conformance_tests=("test_cpu_profile_metadata", "test_x86_subset_instruction_vectors", "test_profile_selection_does_not_claim_microarchitecture"),
    ),
    "amd-ryzen-5-5600": CPUProfile(
        profile_id="amd-ryzen-5-5600",
        vendor="AMD",
        model="AMD Ryzen 5 5600 (Zen 3 desktop reference)",
        isa="AMD64",
        specification_urls=(AMD_RYZEN_5600, AMD_APM),
        specification_parameters={
            "physical_cores": 6, "threads": 12, "base_clock_hz": 3_500_000_000,
            "max_boost_clock_hz": 4_400_000_000, "l1_cache_bytes": 393_216,
            "l2_cache_bytes": 3_145_728, "l3_cache_bytes": 33_554_432, "tdp_watts": 65,
        },
        fidelity="functional_subset",
        modeled_behaviors=("the same explicitly listed symbolic x86-inspired subset", "reference metadata for profile selection"),
        unsupported_features=_COMMON_UNSUPPORTED + ("AMD Zen 3 pipeline/cache latency model",),
        conformance_tests=("test_cpu_profile_metadata", "test_x86_subset_instruction_vectors", "test_profile_selection_does_not_claim_microarchitecture"),
    ),
}


def get_cpu_profile(profile_id: str) -> CPUProfile:
    try:
        return CPU_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_CPU_PROFILE:{profile_id}") from exc


def list_cpu_profiles() -> list[dict]:
    return [CPU_PROFILES[key].describe() for key in sorted(CPU_PROFILES)]
