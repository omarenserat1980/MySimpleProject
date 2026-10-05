from __future__ import annotations

"""Fail-closed preflight for the Brain-owned execution runtime."""

from dataclasses import dataclass
from shutil import which
import json
import platform
import os
from pathlib import Path


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


def inspect_runner(runner_id: str = "brain-internal") -> RunnerPreflight:
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
