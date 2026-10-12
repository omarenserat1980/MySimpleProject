"""Unified evidence-first company launch readiness classifier."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass(frozen=True)
class Readiness:
    status: str
    release_allowed: bool
    commercial_allowed: bool
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]


def classify(release_evidence: dict | None, commercial_evidence: dict | None) -> Readiness:
    blockers: list[str] = []
    evidence: list[str] = []

    release = release_evidence or {}
    if release.get("status") == "RELEASE_ALLOWED":
        evidence.append("release_gate=RELEASE_ALLOWED")
    else:
        blockers.append("release_gate_not_allowed")

    commercial = commercial_evidence or {}
    required = ("customer", "delivery", "payment_verified")
    missing = [k for k in required if commercial.get(k) is not True]
    if missing:
        blockers.append("commercial_evidence_missing:" + ",".join(missing))
    else:
        evidence.append("commercial_evidence=verified")

    if not blockers:
        return Readiness("READY", True, True, (), tuple(evidence))
    if release.get("status") == "RELEASE_ALLOWED":
        return Readiness("NEEDS_EVIDENCE", True, False, tuple(blockers), tuple(evidence))
    return Readiness("BLOCKED", False, False, tuple(blockers), tuple(evidence))


def main() -> int:
    p = Path(".brain_state/release_gate/release_gate.json")
    release = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    result = classify(release, None)
    out = Path(".brain_state/company_launch_readiness.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0 if result.status != "READY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
