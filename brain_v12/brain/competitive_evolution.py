"""Reference-capability benchmark tracks for Jet Brain."""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class BenchmarkTrack:
    track_id: str
    reference: str
    focus: str
    target: str
    evidence: str

REFERENCE_COMPANIES: Tuple[str, ...] = ("NVIDIA", "Microsoft", "Apple")
TRACKS: Tuple[BenchmarkTrack, ...] = (
    BenchmarkTrack("AI_INFRA", "NVIDIA", "AI compute and infrastructure", "measured compute and inference", "reproducible benchmark"),
    BenchmarkTrack("CLOUD_AGENTS", "Microsoft", "cloud and autonomous agents", "durable jobs with recovery", "audit and recovery evidence"),
    BenchmarkTrack("PRODUCT_ECOSYSTEM", "Apple", "integrated product experience", "coherent secure workflows", "end-to-end user-flow evidence"),
    BenchmarkTrack("SOFTWARE", "Microsoft", "software delivery", "build test verify release", "reproducible release evidence"),
    BenchmarkTrack("SECURITY", "Microsoft", "defense in depth", "least privilege and fail-closed controls", "security test evidence"),
    BenchmarkTrack("MEDIA", "NVIDIA", "media production", "verified media factory", "master plus QC evidence"),
    BenchmarkTrack("R_AND_D", "NVIDIA", "capability evolution", "predict experiment implement verify learn", "learning record"),
    BenchmarkTrack("OPERATIONS", "Microsoft", "operating discipline", "measurable service lifecycle", "delivery evidence"),
)
PRINCIPLES = ("benchmark_before_claim", "evidence_before_status", "build_before_marketing", "verify_before_delivery", "measure_before_optimization", "learn_before_next_iteration")

def benchmark_tracks():
    return TRACKS

def next_frontier():
    return [t.track_id for t in TRACKS]
