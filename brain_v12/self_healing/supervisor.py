#!/usr/bin/env python3
"""Continuous Brain Supervisor.

Safe-by-default self-healing loop:
1. Run the target command.
2. Capture stdout/stderr and exit status.
3. Diagnose the failure with deterministic rules.
4. Invoke an allowlisted repair command (optional).
5. Re-run verification.
6. Repeat with bounded attempts and exponential backoff.

The supervisor does NOT claim success merely because a repair command ran.
A repair is accepted only when the verification command exits with code 0.

Environment:
  BRAIN_MAX_ATTEMPTS        default 5
  BRAIN_BACKOFF_SECONDS     default 5
  BRAIN_MAX_BACKOFF_SECONDS default 120
  BRAIN_REPAIR_COMMAND      optional command used to create a better candidate
  BRAIN_VERIFY_COMMAND      optional independent verification command
  BRAIN_STATE_DIR           default .brain/state
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


@dataclass
class Attempt:
    number: int
    started_at: str
    exit_code: int
    stdout: str
    stderr: str
    diagnosis: list[str]
    repair_exit_code: int | None = None
    repair_stdout: str = ""
    repair_stderr: str = ""
    verified: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=os.environ.copy(),
    )


def diagnose(stdout: str, stderr: str, exit_code: int) -> list[str]:
    text = (stdout + "\n" + stderr).lower()
    findings: list[str] = []
    rules = (
        ("missing-token", ("token_missing", "token required", "gh_token_required", "github_token_or_gh_token_required")),
        ("permission", ("permission denied", "resource not accessible", "403 forbidden", "insufficient permission")),
        ("network", ("timed out", "timeout", "temporary failure", "connection reset", "urlerror", "name or service not known")),
        ("dependency", ("modulenotfounderror", "no module named", "command not found", "cannot import")),
        ("syntax", ("syntaxerror", "indentationerror")),
        ("test-failure", ("assertionerror", "failed", "failure", "exit code")),
    )
    for name, needles in rules:
        if any(n in text for n in needles):
            findings.append(name)
    if not findings:
        findings.append("unknown-failure")
    if exit_code == 0:
        findings.append("no-runtime-error")
    return findings


def safe_env() -> dict[str, str]:
    # Do not persist secrets in state files.
    blocked = ("TOKEN", "SECRET", "PASSWORD", "KEY", "COOKIE")
    return {
        k: ("<REDACTED>" if any(x in k.upper() for x in blocked) else v)
        for k, v in os.environ.items()
    }


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def verify(command: str | None, timeout: int) -> tuple[bool, str, str, int]:
    if not command:
        return True, "", "", 0
    p = run(command, timeout)
    return p.returncode == 0, p.stdout, p.stderr, p.returncode


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Brain continuous self-healing supervisor")
    p.add_argument("--command", required=True, help="Command to execute")
    p.add_argument("--verify", default=os.getenv("BRAIN_VERIFY_COMMAND"))
    p.add_argument("--repair", default=os.getenv("BRAIN_REPAIR_COMMAND"))
    p.add_argument("--max-attempts", type=int, default=int(os.getenv("BRAIN_MAX_ATTEMPTS", "5")))
    p.add_argument("--backoff", type=float, default=float(os.getenv("BRAIN_BACKOFF_SECONDS", "5")))
    p.add_argument("--max-backoff", type=float, default=float(os.getenv("BRAIN_MAX_BACKOFF_SECONDS", "120")))
    p.add_argument("--timeout", type=int, default=int(os.getenv("BRAIN_COMMAND_TIMEOUT", "900")))
    p.add_argument("--state", default=os.getenv("BRAIN_STATE_DIR", ".brain/state"))
    p.add_argument("--continue-on-success", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts must be >= 1")

    state_dir = Path(args.state)
    history_path = state_dir / "self_healing_history.json"
    lock_path = state_dir / "supervisor.lock"
    if lock_path.exists():
        print("BRAIN_SUPERVISOR_ALREADY_RUNNING")
        return 3
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(f"{os.getpid()} {utc_now()}\n", encoding="utf-8")

    attempts: list[Attempt] = []
    final_code = 1
    try:
        for n in range(1, args.max_attempts + 1):
            started = utc_now()
            try:
                p = run(args.command, args.timeout)
                diagnosis = diagnose(p.stdout, p.stderr, p.returncode)
                item = Attempt(n, started, p.returncode, p.stdout[-20000:], p.stderr[-20000:], diagnosis)

                if p.returncode == 0:
                    ok, vo, ve, vc = verify(args.verify, args.timeout)
                    item.verified = ok
                    item.stdout = (item.stdout + "\n[VERIFY]\n" + vo)[-20000:]
                    item.stderr = (item.stderr + "\n[VERIFY]\n" + ve)[-20000:]
                    item.exit_code = vc if not ok else 0
                    attempts.append(item)
                    if ok:
                        final_code = 0
                        print(f"BRAIN_HEALING_SUCCESS attempt={n}")
                        break
                else:
                    attempts.append(item)

                if n >= args.max_attempts:
                    break

                # The repair command is deliberately explicit and replaceable.
                # It may generate/edit code, but success is impossible without verification.
                if args.repair:
                    # Give the repair agent a bounded, secret-redacted failure report.
                    # The agent can improve code based on concrete evidence rather than guessing.
                    failure_report = state_dir / "current_failure.json"
                    write_state(failure_report, {
                        "schema": "brain-repair-context/v1",
                        "attempt": n,
                        "exit_code": item.exit_code,
                        "diagnosis": item.diagnosis,
                        "stdout": item.stdout[-12000:],
                        "stderr": item.stderr[-12000:],
                        "command": args.command,
                        "verify_command": args.verify,
                    })
                    repair_env = os.environ.copy()
                    repair_env["BRAIN_FAILURE_FILE"] = str(failure_report)
                    repair = subprocess.run(
                        args.repair,
                        shell=True,
                        text=True,
                        capture_output=True,
                        timeout=args.timeout,
                        env=repair_env,
                    )
                    item.repair_exit_code = repair.returncode
                    item.repair_stdout = repair.stdout[-12000:]
                    item.repair_stderr = repair.stderr[-12000:]

                delay = min(args.max_backoff, args.backoff * (2 ** (n - 1)))
                print(f"BRAIN_HEALING_RETRY attempt={n + 1} sleep={delay:g}s")
                time.sleep(delay)

            except subprocess.TimeoutExpired as exc:
                attempts.append(Attempt(
                    n, started, 124,
                    str(exc.stdout or "")[-20000:],
                    str(exc.stderr or "")[-20000:],
                    ["timeout"],
                ))
                if n < args.max_attempts:
                    time.sleep(min(args.max_backoff, args.backoff * (2 ** (n - 1))))
            except Exception as exc:
                attempts.append(Attempt(
                    n, started, 1, "", traceback.format_exc()[-20000:], ["supervisor-error"]
                ))
                if n < args.max_attempts:
                    time.sleep(min(args.max_backoff, args.backoff * (2 ** (n - 1))))

        state = {
            "schema": "brain-self-healing/v1",
            "status": "VERIFIED_COMPLETED" if final_code == 0 else "FAILED_AFTER_REPAIR_ATTEMPTS",
            "finished_at": utc_now(),
            "command": args.command,
            "verify_command": args.verify,
            "max_attempts": args.max_attempts,
            "attempts": [asdict(x) for x in attempts],
            "environment": safe_env(),
        }
        write_state(history_path, state)
        print(json.dumps({
            "status": state["status"],
            "attempts": len(attempts),
            "history": str(history_path),
        }, ensure_ascii=False))
        return final_code
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
