"""Autonomous Brain capability selection for cinematic demonstrations."""
from __future__ import annotations
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "STATE" / "capability_demo"
DECISION = STATE / "decision.json"

CAPABILITIES = (
    ("cinematic_direction", "Demonstrate autonomous cinematic direction, production and verification."),
    ("self_verification", "Demonstrate planning followed by independent media verification."),
    ("failure_recovery", "Demonstrate bounded retries and refusal to promote an unverified master."),
    ("cloud_only_execution", "Demonstrate production entirely through Brain Cloud."),
)

def choose() -> dict:
    index = int(os.getenv("BRAIN_DEMO_CAPABILITY_INDEX", "0")) % len(CAPABILITIES)
    key, objective = CAPABILITIES[index]
    return {
        "status": "DECIDED",
        "capability": key,
        "objective": objective,
        "decision_basis": ["autonomy", "cinematic_capability", "verification", "cloud_only"],
        "runtime": "brain_cloud",
        "device_required": False,
        "termux_required": False,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    decision = choose()
    DECISION.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
