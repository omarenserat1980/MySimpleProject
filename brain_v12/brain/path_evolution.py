"""Brain Path Evolution Registry.

Keeps reusable execution/search/inspection paths ranked by evidence.
The registry is intentionally append-only at the record level: new observations
create new versions instead of silently rewriting history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time
from typing import Any


@dataclass
class PathRecord:
    path_id: str
    goal: str
    steps: list[str]
    status: str = "candidate"
    score: float = 0.0
    source_strategy: str = "local"
    open_source_regions: list[str] | None = None
    license_required: str = "compatible"
    runs: int = 0
    successes: int = 0
    failures: int = 0
    avg_seconds: float | None = None
    last_error: str | None = None
    evidence: list[str] | None = None

    def __post_init__(self) -> None:
        if self.evidence is None:
            self.evidence = []
        if self.open_source_regions is None:
            self.open_source_regions = []

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0


class PathEvolutionRegistry:
    """Selects proven paths while preserving evidence and avoiding dead ends."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {"version": 1, "updated_at": None, "paths": {}}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self._data["updated_at"] = time.time()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def upsert(self, record: PathRecord) -> None:
        self._data["paths"][record.path_id] = asdict(record)
        self.save()

    def record_run(
        self,
        path_id: str,
        *,
        success: bool,
        seconds: float | None = None,
        error: str | None = None,
        evidence: str | None = None,
    ) -> None:
        raw = self._data["paths"].get(path_id)
        if raw is None:
            raise KeyError(path_id)
        raw["runs"] += 1
        raw["successes"] += int(success)
        raw["failures"] += int(not success)
        if seconds is not None:
            previous = raw.get("avg_seconds")
            raw["avg_seconds"] = seconds if previous is None else ((previous * (raw["runs"] - 1) + seconds) / raw["runs"])
        raw["last_error"] = None if success else error
        if evidence:
            raw.setdefault("evidence", []).append(evidence)
            raw["evidence"] = raw["evidence"][-20:]
        raw["score"] = self._score(raw)
        raw["status"] = "proven" if success and raw["successes"] >= 2 else ("degraded" if raw["failures"] else "candidate")
        self.save()

    @staticmethod
    def _score(raw: dict[str, Any]) -> float:
        rate = raw["successes"] / raw["runs"] if raw["runs"] else 0.0
        speed = 1.0 if raw.get("avg_seconds") is None else 1.0 / max(raw["avg_seconds"], 0.1)
        # Reliability dominates speed; speed breaks ties between reliable paths.
        return round(rate * 100.0 + min(speed * 10.0, 20.0), 4)

    def best(self, goal: str | None = None) -> PathRecord | None:
        candidates = []
        for raw in self._data["paths"].values():
            if goal and raw["goal"] != goal:
                continue
            candidates.append(raw)
        if not candidates:
            return None
        raw = max(candidates, key=lambda item: item.get("score", 0.0))
        return PathRecord(**raw)

    def source_policy(self) -> dict[str, Any]:
        return {
            "strategy": "global-open-source-evidence-first",
            "regions": ["US", "China", "India", "Germany", "UK", "Canada", "Japan", "South Korea", "Israel", "Singapore"],
            "rules": ["search mature open-source implementations first", "check license compatibility", "check security and maintenance", "adapt only after local reproduction and tests", "record source and evidence"],
        }

    def snapshot(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._data))


def default_registry(root: str | Path = ".") -> PathEvolutionRegistry:
    return PathEvolutionRegistry(Path(root) / ".brain" / "state" / "path_evolution.json")



def bootstrap_default_paths(registry: PathEvolutionRegistry) -> None:
    """Install stable baseline paths once; never overwrite observed metrics."""
    defaults = [
        ("PATH-BUILD-APK", "build", ["source", "ci-build", "artifact", "checksum", "install", "verify"]),
        ("PATH-TERMUX-BRAIN", "connectivity", ["api", "enqueue", "redmi3-01", "execute", "report", "verify"]),
        ("PATH-ANDROID-EXECUTOR", "connectivity", ["apk", "android-executor-redmi3-01", "poll", "task", "result", "verify"]),
        ("PATH-FAST-SCAN", "scan", ["github", "ci", "runtime", "device", "deep-scan-on-demand"]),
        ("PATH-FAST-RECOVERY", "recovery", ["evidence", "classify", "best-alternative", "one-repair", "verify", "record"]),
        ("PATH-GLOBAL-OPEN-SOURCE", "open-source", ["problem", "global-source-search", "license-check", "security-check", "local-adapt", "test", "verify", "record"]),
    ]
    for path_id, goal, steps in defaults:
        if path_id not in registry._data["paths"]:
            registry.upsert(PathRecord(path_id, goal, steps))
