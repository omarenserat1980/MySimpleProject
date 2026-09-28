"""15000-cycle autonomous repair controller for the Electronic Brain factory.

The controller repeatedly performs: inspect -> repair -> verify -> checkpoint.
It is intentionally bounded at 15,000 controller cycles. Each repair attempt is
still governed by the conservative allowlisted self-healer. A cycle is accepted
only when verification passes. Optional factory execution can feed its failure
back into the next repair cycle.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_CONTROLLER_CYCLES = 15000
CHECKPOINT_EVERY = 10
DEFAULT_REPORT = "repair_15000_report.json"


def run(cmd: list[str], *, timeout: int = 600, env: dict[str, str] | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, **(env or {})},
    )
    return p.returncode, (p.stdout + p.stderr)[-12000:]


def load_error(path: str) -> str:
    if not path:
        return os.getenv("FACTORY_LAST_ERROR", "")
    try:
        return Path(path).read_text(encoding="utf-8")[-12000:]
    except OSError as exc:
        return f"error-file-read-failed: {exc}"


def save(report_path: Path, report: dict) -> None:
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def controller(error_text: str = "", *, run_factory: bool = False,
               max_cycles: int = MAX_CONTROLLER_CYCLES,
               report_path: str = DEFAULT_REPORT) -> dict:
    max_cycles = max(1, min(int(max_cycles), MAX_CONTROLLER_CYCLES))
    report_file = ROOT / report_path
    history: list[dict] = []
    current_error = error_text
    started = time.time()

    for cycle in range(1, max_cycles + 1):
        cycle_started = time.time()
        healer_report = ROOT / f".repair_cycle_{cycle}.json"
        rc, healer_out = run(
            ["python", "-m", "brain_v7.braincore_v2.code_self_healer",
             "--report", str(healer_report)],
            timeout=600,
            env={"FACTORY_LAST_ERROR": current_error},
        )

        healer = {}
        if healer_report.exists():
            try:
                healer = json.loads(healer_report.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                healer = {"status": "INVALID_HEALER_REPORT"}

        verification_ok = healer.get("status") == "CODE_VERIFIED" and rc == 0
        factory_ok = None
        factory_output = ""

        if verification_ok and run_factory:
            frc, factory_output = run(
                ["python", "-m", "brain_v7.braincore_v2.background_factory_worker"],
                timeout=3600,
            )
            factory_ok = frc == 0
            if not factory_ok:
                current_error = factory_output

        entry = {
            "cycle": cycle,
            "healer_status": healer.get("status"),
            "healer_returncode": rc,
            "healer_cycles": healer.get("cycles_completed"),
            "changed_files": healer.get("changed_files", []),
            "verification_ok": verification_ok,
            "factory_ok": factory_ok,
            "factory_output_tail": factory_output[-4000:] if factory_output else "",
            "elapsed_seconds": round(time.time() - cycle_started, 3),
        }
        history.append(entry)

        report = {
            "status": "RUNNING",
            "max_controller_cycles": max_cycles,
            "cycles_completed": cycle,
            "started_at": started,
            "history": history[-100:],
            "last_error": current_error[-12000:],
        }
        save(report_file, report)

        # A clean code verification ends the repair phase. If factory mode was
        # requested, only a verified factory run ends the complete controller.
        if verification_ok and (not run_factory or factory_ok):
            report["status"] = "VERIFIED_SUCCESS"
            save(report_file, report)
            return report

        if cycle % CHECKPOINT_EVERY == 0:
            save(report_file, report)

        # Do not spin on an unchanged, unrecoverable error forever.
        if not healer.get("changed_files") and not verification_ok:
            report["status"] = "NO_ALLOWLISTED_REPAIR"
            save(report_file, report)
            return report

    report = {
        "status": "CONTROLLER_LIMIT_REACHED",
        "max_controller_cycles": max_cycles,
        "cycles_completed": len(history),
        "started_at": started,
        "history": history[-100:],
        "last_error": current_error[-12000:],
    }
    save(report_file, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--error-file", default="")
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--max-cycles", type=int, default=MAX_CONTROLLER_CYCLES)
    parser.add_argument("--run-factory", action="store_true")
    args = parser.parse_args()
    result = controller(
        load_error(args.error_file),
        run_factory=args.run_factory,
        max_cycles=args.max_cycles,
        report_path=args.report,
    )
    print(json.dumps({
        "status": result["status"],
        "cycles_completed": result["cycles_completed"],
        "max_controller_cycles": result["max_controller_cycles"],
    }, ensure_ascii=False))
    return 0 if result["status"] == "VERIFIED_SUCCESS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
