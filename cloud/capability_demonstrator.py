"""Autonomous Brain capability selection for cinematic demonstrations."""
from __future__ import annotations
import json, os, subprocess, sys, time
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
    env = os.environ.copy()
    env["BRAIN_DEMO_CAPABILITY"] = decision["capability"]
    env["BRAIN_DEMO_OBJECTIVE"] = decision["objective"]
    plan_rc = subprocess.run([sys.executable, "-m", "cloud.capability_film"], cwd=ROOT, env=env, check=False).returncode
    if plan_rc != 0:
        decision["execution_status"] = "FAILED_PLAN"
        DECISION.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return plan_rc
    env["BRAIN_CINEMATIC_PLAN"] = str(ROOT / "brain_v12" / "movie_summary_factory" / "jobs" / "room-13-horror-10m-cinematic-v3.json")
    result = subprocess.run(
        [sys.executable, "-m", "brain_v12.cinematic_autopilot"],
        cwd=ROOT, env=env, check=False,
    )
    decision["execution_return_code"] = result.returncode
    decision["execution_status"] = "COMPLETED" if result.returncode == 0 else "FAILED"
    DECISION.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
