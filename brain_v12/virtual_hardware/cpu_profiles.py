"""CPU profile metadata and explicit fidelity boundaries for Brain's virtual CPU.

Processor names identify documented reference hardware for profile provenance; they
do not turn BrainVM instructions into that processor's native ISA.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class CPUProfile:
    name: str
    vendor: str
    reference_model: str
    architecture: str
    reference_url: str
    isa_spec_url: str
    nominal_clock_hz: int
    cache_l1_bytes: int
    cache_l2_bytes: int
    cache_l3_bytes: int
    cache_line_bytes: int = 64
    cache_hit_cycles: int = 1
    l2_hit_cycles: int = 4
    l3_hit_cycles: int = 12
    memory_cycles: int = 80
    fidelity: str = "functional-brainvm-plus-statistical-cost-model"
    native_isa_supported: bool = False

    def metadata(self) -> dict:
        result = asdict(self)
        result["status"] = "REFERENCE_PROFILE_NOT_NATIVE_ISA_EMULATION"
        result["timing_is_estimated"] = True
        result["cycle_accurate"] = False
        result["pipeline_model"] = "not modeled; one BrainVM instruction retires atomically"
        return result

PROFILES = {
    "brainvm-baseline": CPUProfile(
        name="brainvm-baseline", vendor="Electronic Brain",
        reference_model="Synthetic deterministic BrainVM baseline",
        architecture="BrainVM-1 custom tuple ISA",
        reference_url="https://github.com/omarenserat1980/MySimpleProject",
        isa_spec_url="https://github.com/omarenserat1980/MySimpleProject",
        nominal_clock_hz=1_000_000_000, cache_l1_bytes=16*1024,
        cache_l2_bytes=256*1024, cache_l3_bytes=0),
    "intel-core-i7-12700k-reference": CPUProfile(
        name="intel-core-i7-12700k-reference", vendor="Intel",
        reference_model="Core i7-12700K (Alder Lake-S; heterogeneous P/E cores)",
        architecture="x86-64 hardware reference; BrainVM ISA remains active",
        reference_url="https://www.intel.com/content/www/us/en/products/sku/134599/intel-core-i712700k-processor-25m-cache-up-to-5-00-ghz/specifications.html",
        isa_spec_url="https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html",
        nominal_clock_hz=3_600_000_000, cache_l1_bytes=80*1024,
        cache_l2_bytes=1_250*1024, cache_l3_bytes=25*1024*1024),
    "amd-epyc-9654-reference": CPUProfile(
        name="amd-epyc-9654-reference", vendor="AMD",
        reference_model="EPYC 9654 (Zen 4, Genoa)",
        architecture="x86-64 hardware reference; BrainVM ISA remains active",
        reference_url="https://www.amd.com/en/products/cpu/amd-epyc-9654",
        isa_spec_url="https://www.amd.com/en/search/documentation/hub.html",
        nominal_clock_hz=2_400_000_000, cache_l1_bytes=64*1024,
        cache_l2_bytes=1*1024*1024, cache_l3_bytes=384*1024*1024),
}

def get_cpu_profile(name: str) -> CPUProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"CPU_PROFILE_UNSUPPORTED:{name}") from exc
