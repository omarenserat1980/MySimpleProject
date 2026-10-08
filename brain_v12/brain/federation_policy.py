from __future__ import annotations

"""Policy for selecting real Brain nodes for federated workloads."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class NodeScore:
    provider_id: str
    score: float
    reasons: tuple[str, ...]


def score_nodes(resources: Iterable[dict], *, required_kinds: set[str] | None = None,
                prefer_local: bool = False) -> list[NodeScore]:
    required_kinds = required_kinds or set()
    nodes: dict[str, dict] = {}
    for r in resources:
        provider = str(r.get("provider_id") or "")
        if not provider:
            continue
        node = nodes.setdefault(provider, {"kinds": set(), "degraded": 0, "available": 0})
        node["kinds"].add(str(r.get("kind")))
        node["available"] += 1
        if str(r.get("state")) == "DEGRADED":
            node["degraded"] += 1

    out = []
    for provider, node in nodes.items():
        missing = required_kinds - node["kinds"]
        score = 100.0
        reasons = []
        if missing:
            score -= 60.0 * len(missing)
            reasons.append("missing:" + ",".join(sorted(missing)))
        score -= 10.0 * node["degraded"]
        if node["degraded"]:
            reasons.append("degraded")
        if prefer_local and provider in {"host", "localhost"}:
            score += 5.0
            reasons.append("local-preferred")
        out.append(NodeScore(provider, score, tuple(reasons)))
    return sorted(out, key=lambda x: (-x.score, x.provider_id))
