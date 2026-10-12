#!/usr/bin/env python3
"""Evidence-first doctor for the existing Electronic Brain ChatGPT emulator.

Read-only by default. It never prints credentials. A live chat test is opt-in
because it creates a session and may call the configured model provider.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

CHECKS = (
    ("health", "/health"),
    ("brain_ai_status", "/api/brain-ai/status"),
    ("chat_sessions", "/api/brain-chat/sessions"),
)


def resolve_origin(explicit: str | None) -> str:
    raw = explicit or os.getenv("BRAIN_API_ORIGIN") or os.getenv("BRAIN_ORIGIN") or ""
    return raw.strip().rstrip("/")


def validate_origin(origin: str) -> str | None:
    if not origin:
        return "API_ORIGIN_MISSING"
    parsed = urllib.parse.urlparse(origin)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        return "API_ORIGIN_MUST_BE_HTTPS (HTTP is allowed only for loopback testing)"
    if not parsed.netloc or parsed.username or parsed.password:
        return "API_ORIGIN_INVALID"
    return None


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None,
                 timeout: float = 8.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Accept": "application/json", **({"Content-Type": "application/json"} if data else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                return {"ok": False, "status": response.status, "error": "RESPONSE_TOO_LARGE"}
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {"ok": False, "status": response.status, "error": "NON_JSON_RESPONSE"}
            return {"ok": 200 <= response.status < 300, "status": response.status,
                    "json": body if isinstance(body, dict) else {"response_type": type(body).__name__}}
    except urllib.error.HTTPError as exc:
        # Do not print response bodies; they may contain implementation details.
        return {"ok": False, "status": exc.code, "error": "HTTP_ERROR"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        category = type(reason).__name__ if reason is not None else type(exc).__name__
        return {"ok": False, "error": "CONNECTION_ERROR", "reason_type": category}


def run(origin: str, send_test_message: bool = False, timeout: float = 8.0) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "electronic-brain.chatgpt-connection-doctor.v1",
        "origin_configured": bool(origin),
        "origin_source": os.getenv("BRAIN_API_ORIGIN_SOURCE", "explicit-or-environment"),
        "checks": {},
        "chat_test": {"requested": send_test_message, "performed": False},
        "success": False,
    }
    problem = validate_origin(origin)
    if problem:
        report["blocker"] = problem
        return report

    for name, path in CHECKS:
        result = request_json(origin + path, timeout=timeout)
        report["checks"][name] = result
        if result.get("ok") and name == "brain_ai_status":
            # A 200 response alone is not enough if the API explicitly reports failure.
            body = result.get("json", {})
            if body.get("ok") is False or body.get("available") is False:
                result["ok"] = False
                result["error"] = "BRAIN_AI_REPORTS_UNAVAILABLE"

    if send_test_message and all(report["checks"].get(k, {}).get("ok") for k, _ in CHECKS):
        report["chat_test"]["performed"] = True
        created = request_json(
            origin + "/api/brain-chat/sessions",
            method="POST",
            payload={"title": "Connection Doctor (safe test)"},
            timeout=timeout,
        )
        report["chat_test"]["session_create"] = {
            k: v for k, v in created.items() if k != "json"
        }
        session = created.get("json", {}).get("session", {}) if created.get("ok") else {}
        session_id = session.get("id") or session.get("session_id")
        if session_id:
            # Safe mode: no tool/action approval is granted.
            message = request_json(
                origin + "/api/brain-chat/sessions/" + urllib.parse.quote(str(session_id), safe="") + "/messages",
                method="POST",
                payload={
                    "message": "Connection diagnostic. Reply exactly: BRAIN_CHAT_CONNECTION_OK",
                    "approved": False,
                    "client_message_id": "brain-connection-doctor-v1",
                },
                timeout=timeout,
            )
            body = message.get("json", {})
            response = body.get("response", {}) if isinstance(body, dict) else {}
            reply = response.get("content", "") if isinstance(response, dict) else ""
            report["chat_test"]["message"] = {
                "ok": bool(message.get("ok") and body.get("ok") and reply),
                "status": message.get("status"),
                "reply_received": bool(reply),
                "reply_marker_match": "BRAIN_CHAT_CONNECTION_OK" in str(reply),
                "model": response.get("model") if isinstance(response, dict) else None,
                "mode": response.get("mode") if isinstance(response, dict) else None,
                "error": response.get("error") if isinstance(response, dict) else None,
            }
        else:
            report["chat_test"]["message"] = {"ok": False, "error": "SESSION_ID_MISSING"}

    probes_ok = all(report["checks"].get(k, {}).get("ok") for k, _ in CHECKS)
    chat_ok = (not send_test_message) or bool(report["chat_test"].get("message", {}).get("ok"))
    report["success"] = bool(probes_ok and chat_ok)
    if not probes_ok:
        report["blocker"] = "ONE_OR_MORE_API_PROBES_FAILED"
    elif send_test_message and not chat_ok:
        report["blocker"] = "LIVE_CHAT_TEST_FAILED"
    else:
        report["blocker"] = None
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", help="Brain API origin (prefer HTTPS; loopback HTTP is allowed)")
    parser.add_argument("--send-test-message", action="store_true",
                        help="Create a test chat session and send one approved=false diagnostic message")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--output", help="Optional path to write the JSON report")
    args = parser.parse_args()
    report = run(resolve_origin(args.origin), args.send_test_message, max(1.0, args.timeout))
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    print(encoded)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
