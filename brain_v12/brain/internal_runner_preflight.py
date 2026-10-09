from __future__ import annotations

"""Fail-closed preflight for the Brain-owned execution runtime."""

from dataclasses import dataclass
from shutil import which
import json
import platform
import os
from pathlib import Path

from .performance import ShortTTLCache, performance_cache_ttl


REQUIRED_BINARIES = (
    "qemu-system-x86_64",
    "qemu-img",
    "xorriso",
    "wimlib-imagex",
    "mkfs.vfat",
    "mcopy",
)


@dataclass(frozen=True)
class RunnerPreflight:
    runner_id: str
    online: bool
    os: str
    arch: str
    binaries: dict[str, bool]
    reasons: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return self.online and not self.reasons and all(self.binaries.values())

    def evidence(self) -> dict:
        return {
            "runner_id": self.runner_id,
            "online": self.online,
            "verified": self.verified,
            "os": self.os,
            "arch": self.arch,
            "binaries": self.binaries,
            "reasons": list(self.reasons),
        }


_PREFLIGHT_CACHE: ShortTTLCache[RunnerPreflight] | None = None


def _cache() -> ShortTTLCache[RunnerPreflight]:
    global _PREFLIGHT_CACHE
    if _PREFLIGHT_CACHE is None:
        _PREFLIGHT_CACHE = ShortTTLCache(performance_cache_ttl())
    return _PREFLIGHT_CACHE


def _inspect_runner_uncached(runner_id: str) -> RunnerPreflight:
    binaries = {name: which(name) is not None for name in REQUIRED_BINARIES}
    reasons: list[str] = []

    if os.environ.get("BRAIN_INTERNAL_RUNNER_FLAG") != "1":
        reasons.append("INTERNAL_RUNNER_FLAG_MISSING")
    if platform.system() != "Linux":
        reasons.append("HOST_OS_NOT_LINUX")
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        reasons.append("HOST_ARCH_NOT_X64")
    if not all(binaries.values()):
        reasons.append("REQUIRED_TOOL_MISSING")

    return RunnerPreflight(
        runner_id=runner_id,
        online=(os.environ.get("BRAIN_INTERNAL_RUNNER_FLAG") == "1"),
        os=platform.system(),
        arch=platform.machine(),
        binaries=binaries,
        reasons=tuple(reasons),
    )


def inspect_runner(runner_id: str = "brain-internal") -> RunnerPreflight:
    # Cache only verified substrate results. Failed probes always execute fresh,
    # so a transient failure cannot be hidden. Authority/contracts/evidence are
    # deliberately outside this cache and remain live on every execution.
    key = f"{runner_id}:{os.environ.get('BRAIN_INTERNAL_RUNNER_FLAG', '')}"
    return _cache().get_or_compute(
        key,
        lambda: _inspect_runner_uncached(runner_id),
        cacheable=lambda result: result.verified,
    )


def invalidate_preflight_cache() -> None:
    if _PREFLIGHT_CACHE is not None:
        _PREFLIGHT_CACHE.invalidate()


def verify_and_write(path: str | Path) -> dict:
    result = inspect_runner()
    evidence = result.evidence()
    Path(path).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    if not result.verified:
        raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED:" + ",".join(result.reasons))
    return evidence


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--evidence", default="brain-internal-runner-preflight.json")
    args = p.parse_args()
    print(json.dumps(verify_and_write(args.evidence), indent=2, sort_keys=True))
