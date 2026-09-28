"""Autonomous inspect -> repair -> verify -> cinematic smoke application.
Safe by design: it delegates source edits to the allowlisted code self-healer,
then runs compile/tests and an optional short factory smoke test.
"""
from __future__ import annotations
import argparse, json, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run(cmd: list[str], timeout: int = 600) -> tuple[int,str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)[-12000:]

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=15000)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--report", default="auto_repair_app_report.json")
    args=ap.parse_args()
    started=time.time()
    report={"status":"RUNNING","started_at":started,"controller_limit":max(1,min(args.cycles,15000))}

    rc,out=run(["python","-m","brain_v7.braincore_v2.repair_controller_15000",
                "--max-cycles",str(report["controller_limit"]),
                "--report","repair_15000_report.json"] + (["--run-factory"] if args.smoke else []),
             timeout=3600 if args.smoke else 900)
    report["controller_returncode"]=rc
    report["controller_output_tail"]=out[-6000:]
    p=ROOT/"repair_15000_report.json"
    if p.exists():
        try: report["controller"]=json.loads(p.read_text(encoding="utf-8"))
        except Exception: report["controller"]={"status":"INVALID_REPORT"}

    if report.get("controller",{}).get("status") not in {"VERIFIED_SUCCESS"}:
        report["status"]="REPAIR_NOT_VERIFIED"
    else:
        report["status"]="VERIFIED"

    report["elapsed_seconds"]=round(time.time()-started,2)
    (ROOT/args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":report["status"],"elapsed_seconds":report["elapsed_seconds"]},ensure_ascii=False))
    return 0 if report["status"]=="VERIFIED" else 2

if __name__=="__main__":
    raise SystemExit(main())
