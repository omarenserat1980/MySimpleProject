"""Pull-based bridge from a trusted GitHub issue to Brain's owned virtual emulator.

This is a narrow relay, not a remote shell:
- accepts one exact task envelope from an allowlisted GitHub author;
- performs only GET /api/remote-fabric/status on loopback port 8012;
- records hashed local evidence, comments the sanitized result, then closes the issue;
- never accepts arbitrary commands, URLs, headers, or host/device targets.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_REPOSITORY = "omarenserat1980/MySimpleProject"
TASK_TITLE = "[BRAIN-EMU] STATUS"
TASK_BODY = "task=status"
STATUS_URL = "http://127.0.0.1:8012/api/remote-fabric/status"
SCHEMA = "brain.owned-emulator-chat-bridge.v1"


@dataclass(frozen=True)
class BridgeConfig:
    repository: str = DEFAULT_REPOSITORY
    allowed_authors: frozenset[str] = frozenset()
    status_url: str = STATUS_URL
    evidence_dir: Path = Path(".brain/owned_emulator_bridge/evidence")
    request_timeout: float = 5.0
    gh_timeout: float = 15.0

    def validate(self) -> None:
        if not self.repository or "/" not in self.repository:
            raise ValueError("INVALID_REPOSITORY")
        parsed = urllib.parse.urlparse(self.status_url)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.port != 8012 or parsed.path != "/api/remote-fabric/status"
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError("STATUS_URL_MUST_BE_LOOPBACK_BRAIN_STATUS_ENDPOINT")
        if not self.allowed_authors:
            raise ValueError("BRAIN_BRIDGE_ALLOWED_GITHUB_LOGINS_REQUIRED")


def _gh(args: list[str], timeout: float) -> str:
    if shutil.which("gh") is None:
        raise RuntimeError("GITHUB_CLI_NOT_INSTALLED")
    completed = subprocess.run(
        ["gh", *args], check=False, capture_output=True, text=True,
        timeout=timeout, shell=False,
    )
    if completed.returncode != 0:
        # Do not echo stderr: it can contain local account or environment details.
        raise RuntimeError(f"GITHUB_CLI_FAILED_EXIT_{completed.returncode}")
    return completed.stdout


def list_open_issues(config: BridgeConfig) -> list[dict[str, Any]]:
    raw = _gh([
        "issue", "list", "--repo", config.repository, "--state", "open",
        "--limit", "100", "--json", "number,title,body,author,url",
    ], config.gh_timeout)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError("GITHUB_ISSUE_LIST_INVALID")
    return [x for x in data if isinstance(x, dict)]


def _author_login(issue: dict[str, Any]) -> str:
    author = issue.get("author")
    return str(author.get("login", "")) if isinstance(author, dict) else ""


def is_authorized_status_task(issue: dict[str, Any], config: BridgeConfig) -> bool:
    return (
        issue.get("title") == TASK_TITLE
        and str(issue.get("body", "")).strip() == TASK_BODY
        and _author_login(issue) in config.allowed_authors
        and isinstance(issue.get("number"), int)
        and issue["number"] > 0
    )


def fetch_status(config: BridgeConfig) -> dict[str, Any]:
    config.validate()
    # Use a direct loopback HTTPConnection: no proxy environment, redirect handling,
    # configurable host, or URL path can move this request away from Brain.
    connection = http.client.HTTPConnection("127.0.0.1", 8012, timeout=config.request_timeout)
    try:
        connection.request(
            "GET", "/api/remote-fabric/status",
            headers={"Accept": "application/json", "User-Agent": "ElectronicBrain-OwnedEmulatorBridge/1"},
        )
        response = connection.getresponse()
        http_status = int(response.status)
        if http_status != 200:
            return {"ok": False, "http_status": http_status, "status": "HTTP_ERROR"}
        raw = response.read(65537)
    except (TimeoutError, socket.timeout):
        return {"ok": False, "http_status": None, "status": "TIMEOUT"}
    except (OSError, http.client.HTTPException):
        return {"ok": False, "http_status": None, "status": "CONNECTION_ERROR"}
    finally:
        connection.close()

    if len(raw) > 65536:
        return {"ok": False, "http_status": http_status, "status": "RESPONSE_TOO_LARGE"}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "http_status": http_status, "status": "INVALID_JSON"}
    if not isinstance(payload, dict):
        return {"ok": False, "http_status": http_status, "status": "INVALID_RESPONSE_SHAPE"}

    # Return only an explicit allowlist; do not relay arbitrary server fields.
    heartbeat = payload.get("heartbeat")
    safe = {
        "ok": payload.get("ok") if isinstance(payload.get("ok"), bool) else None,
        "mode": payload.get("mode") if isinstance(payload.get("mode"), str) else None,
        "reality": payload.get("reality") if isinstance(payload.get("reality"), str) else None,
        "policy": payload.get("policy") if isinstance(payload.get("policy"), str) else None,
        "status": payload.get("status") if isinstance(payload.get("status"), str) else None,
        "heartbeat": {
            "state": heartbeat.get("state") if isinstance(heartbeat, dict) and isinstance(heartbeat.get("state"), str) else None,
            "node_id": heartbeat.get("node_id") if isinstance(heartbeat, dict) and isinstance(heartbeat.get("node_id"), str) else None,
        } if isinstance(heartbeat, dict) else None,
    }
    # A valid HTTP response is not enough: the gateway must explicitly prove the virtual mode.
    safe["verified_simulation"] = safe["mode"] == "VIRTUAL" and safe["reality"] == "SIMULATED"
    safe["ok"] = bool(safe["ok"] is True and safe["verified_simulation"])
    safe["http_status"] = http_status
    if not safe["verified_simulation"]:
        safe["status"] = "SIMULATION_NOT_VERIFIED"
    return safe

def _read_processed(state_path: Path) -> set[int]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return {int(x) for x in state.get("processed_issue_numbers", [])}
    except FileNotFoundError:
        return set()
    except (ValueError, TypeError, json.JSONDecodeError):
        raise RuntimeError("BRIDGE_STATE_INVALID_FAIL_CLOSED")


def _write_evidence(config: BridgeConfig, issue: dict[str, Any], result: dict[str, Any]) -> Path:
    config.evidence_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": SCHEMA,
        "task": "remote-fabric-status",
        "issue_number": issue["number"],
        "source": "loopback-api",
        "result": result,
        "observed_at_epoch": time.time(),
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    record["sha256"] = hashlib.sha256(canonical).hexdigest()
    path = config.evidence_dir / f"issue-{issue['number']}.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def process_issue(issue: dict[str, Any], config: BridgeConfig, state_path: Path) -> dict[str, Any]:
    config.validate()
    if not is_authorized_status_task(issue, config):
        return {"ok": False, "state": "IGNORED_UNAUTHORIZED_OR_UNSUPPORTED_TASK"}
    processed = _read_processed(state_path)
    number = int(issue["number"])
    if number in processed:
        return {"ok": True, "state": "ALREADY_PROCESSED", "issue_number": number}

    result = fetch_status(config)
    evidence_path = _write_evidence(config, issue, result)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    comment = (
        "Electronic Brain owned-emulator bridge result\n"
        "- task: remote-fabric-status\n"
        f"- result: {json.dumps(result, sort_keys=True, separators=(',', ':'))}\n"
        f"- local evidence: {evidence_path.as_posix()}\n"
        f"- evidence sha256: {evidence['sha256']}\n"
        f"- execution reality: {result.get('reality', 'UNKNOWN')}\n"
        "This bridge only performed a loopback GET; it did not execute a host/device command."
    )
    _gh(["issue", "comment", str(number), "--repo", config.repository, "--body", comment], config.gh_timeout)
    processed.add(number)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"processed_issue_numbers": sorted(processed)}, indent=2) + "\n", encoding="utf-8")
    # Closing is housekeeping only. The durable local state prevents duplicate execution if close fails.
    _gh(["issue", "close", str(number), "--repo", config.repository], config.gh_timeout)
    return {"ok": bool(result.get("ok")), "state": "PROCESSED", "issue_number": number,
            "evidence": str(evidence_path), "result": result}


def run_once(config: BridgeConfig, state_path: Path) -> list[dict[str, Any]]:
    config.validate()
    outcomes = []
    for issue in list_open_issues(config):
        if is_authorized_status_task(issue, config):
            outcomes.append(process_issue(issue, config, state_path))
    return outcomes or [{"ok": True, "state": "IDLE_NO_AUTHORIZED_TASK"}]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poll a trusted GitHub task and probe only Brain's loopback simulation status endpoint.")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("BRAIN_BRIDGE_POLL_SECONDS", "15")))
    parser.add_argument("--repo", default=os.getenv("BRAIN_BRIDGE_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--evidence-dir", default=os.getenv("BRAIN_BRIDGE_EVIDENCE_DIR", ".brain/owned_emulator_bridge/evidence"))
    args = parser.parse_args(argv)
    authors = frozenset(x.strip().lstrip("@") for x in os.getenv("BRAIN_BRIDGE_ALLOWED_GITHUB_LOGINS", "").split(",") if x.strip())
    config = BridgeConfig(repository=args.repo, allowed_authors=authors, evidence_dir=Path(args.evidence_dir))
    state_path = Path(args.evidence_dir).parent / "state.json"
    try:
        config.validate()
        if args.poll_seconds < 5:
            raise ValueError("POLL_INTERVAL_MUST_BE_AT_LEAST_5_SECONDS")
        while True:
            try:
                outcomes = run_once(config, state_path)
                for outcome in outcomes:
                    print(json.dumps(outcome, sort_keys=True), flush=True)
            except Exception as exc:
                print(json.dumps({"ok": False, "state": "BRIDGE_ERROR", "error": f"{type(exc).__name__}:{exc}"}), flush=True)
                if args.once:
                    return 1
            if args.once:
                # A completed poll is not a successful check if the status probe failed closed.
                return 0 if all(outcome.get("ok") is True for outcome in outcomes) else 1
            time.sleep(args.poll_seconds)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "state": "CONFIGURATION_ERROR", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
