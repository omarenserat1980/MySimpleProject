#!/usr/bin/env python3
"""Bounded temporal simulation: explore future states without changing the real system."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
LEDGER = STATE / "temporal_simulation.jsonl"

@dataclass(frozen=True)
class FutureState:
    step: int
    horizon: str
    objective: str
    predicted_risk: str
    preventive_action: str
    confidence: float

def _risk(prediction: dict[str, Any]) -> str:
    return str(prediction.get("risk", "medium")).upper()

def simulate(predictions: list[dict[str, Any]], objective: str, horizons: int = 5) -> dict[str, Any]:
    """Simulate possible future consequences; never mutates production state."""
    horizons = max(1, min(int(horizons), 12))
    states = []
    active = list(predictions)
    for step in range(1, horizons + 1):
        high = [p for p in active if _risk(p) == "HIGH"]
        medium = [p for p in active if _risk(p) != "LOW"]
        risk = "HIGH" if high else ("MEDIUM" if medium else "LOW")
        source = high[0] if high else (medium[0] if medium else {})
        prediction = str(source.get("prediction", "no_known_risk"))
        action = (
            "diagnose_and_prevent:" + str(source.get("id", "unknown"))
            if risk != "LOW" else "continue_verified_path"
        )
        confidence = 0.9 if risk == "HIGH" else (0.7 if risk == "MEDIUM" else 0.5)
        states.append(asdict(FutureState(
            step, f"T+{step}", objective, risk, action, confidence
        )))
        # The simulation propagates the known risk without pretending that it occurred.
        active = [
            {**p, "prediction": prediction, "simulated_step": step}
            for p in active
        ]
    result = {
        "schema": "brain-temporal-simulation/v1",
        "status": "SIMULATED",
        "real_world_changed": False,
        "generated_at": time.time(),
        "objective": objective,
        "future_states": states,
        "recommended_present_action": states[0]["preventive_action"] if states else "observe",
        "evidence": {"prediction_count": len(predictions)},
    }
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result

if __name__ == "__main__":
    from brain_v12.self_healing.future_evolution import predict
    plan = predict()
    result = simulate(plan.get("predictions", []), plan.get("objective", "future evolution"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
