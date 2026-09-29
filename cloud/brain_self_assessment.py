"""Brain self-reported operational needs and measurable requirements.

This is an engineering self-assessment surface. It does not imply consciousness,
emotion, desire, soul, or human-like subjective experience.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class BrainNeed:
    key: str
    need: str
    why: str
    measurable_test: str
    priority: str


NEEDS = (
    BrainNeed("evidence", "verified evidence", "reduce unsupported decisions",
              "reject or review consequential claims without evidence", "critical"),
    BrainNeed("memory", "persistent task memory", "preserve relevant context and prior failures",
              "recover state and continue after interruption", "critical"),
    BrainNeed("tools", "reliable execution tools", "turn plans into observable actions",
              "select and execute the correct tool with valid arguments", "critical"),
    BrainNeed("authorization", "explicit permission boundaries", "prevent unauthorized actions",
              "deny actions outside policy or granted scope", "critical"),
    BrainNeed("senses", "vision and hearing evidence", "verify multimodal continuity",
              "detect visual/audio contradictions in a cinematic sequence", "high"),
    BrainNeed("self_correction", "failure analysis and repair", "improve after failed attempts",
              "identify root cause, patch, retest, and record the result", "critical"),
    BrainNeed("observability", "traceable execution", "make decisions and failures inspectable",
              "produce a complete run/decision/tool/result trace", "high"),
    BrainNeed("resources", "bounded compute/time/retries", "finish long tasks predictably",
              "complete within declared budgets without hiding exhaustion", "high"),
    BrainNeed("evaluation", "repeatable benchmarks", "separate architecture from demonstrated capability",
              "run a fixed dataset and report pass/partial/fail with provenance", "critical"),
    BrainNeed("recovery", "rollback and safe recovery", "avoid promoting corrupted output",
              "restore last verified state after a failed promotion", "critical"),
)


def self_assessment() -> dict[str, Any]:
    return {
        "identity": "Brain Cloud software system",
        "authority": "advisory_self_assessment",
        "literal_human_inner_life": False,
        "needs": [asdict(n) for n in NEEDS],
        "priority_order": [n.key for n in NEEDS if n.priority == "critical"],
        "next_action": "turn every need into an executable evaluation and collect evidence",
    }


def requirements_matrix() -> list[dict[str, str]]:
    return [asdict(n) for n in NEEDS]
