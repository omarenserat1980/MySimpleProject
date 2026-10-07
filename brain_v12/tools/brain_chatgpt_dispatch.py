#!/usr/bin/env python3
"""Dispatch one Brain decision to the configured ChatGPT gateway.

The gateway URL is external to Brain and must be explicitly configured.
No mobile-UI automation or credential scraping is performed.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request

from brain_v12.brain.chatgpt_gateway import create_request, validate_response


def post(url: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": "Electronic-Brain/1.0"}
    token = os.getenv("BRAIN_CHATGPT_GATEWAY_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gateway", default=os.getenv("BRAIN_CHATGPT_GATEWAY_URL", ""))
    p.add_argument("--decision-id", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--constraint", action="append", default=[])
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--action", action="append", default=[])
    args = p.parse_args()

    if not args.gateway:
        print(json.dumps({
            "ok": False,
            "status": "GATEWAY_NOT_CONFIGURED",
            "required_env": "BRAIN_CHATGPT_GATEWAY_URL"
        }, ensure_ascii=False))
        return 2

    request = create_request(
        decision_id=args.decision_id,
        request=args.request,
        objective=args.objective,
        constraints=args.constraint,
        required_evidence=args.evidence,
        allowed_actions=args.action,
    )
    response = post(args.gateway, request)
    validation = validate_response(request, response)
    print(json.dumps({
        "ok": validation["ok"],
        "request": request,
        "response": response,
        "validation": validation,
    }, ensure_ascii=False, indent=2))
    return 0 if validation["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
