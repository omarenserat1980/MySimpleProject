#!/usr/bin/env python3
"""Run a bounded Brain-authority interaction with ChatGPT.

Brain owns the decision. ChatGPT reviews/executes only that decision.
The result is returned to Brain and must be verified before the next cycle.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def call(base: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    key = os.getenv("BRAIN_CONTROL_KEY", "").strip()
    headers = {"Content-Type": "application/json", "User-Agent": "Brain-ChatGPT-Loop/1.0"}
    if key:
        headers["X-BRAIN-CONTROL-KEY"] = key
    data = json.dumps(body or {}).encode() if body is not None else None
    req = urllib.request.Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("V12_BRAIN_URL", "http://127.0.0.1:8012"))
    parser.add_argument("--title", default="Brain → ChatGPT Decision Cycle")
    parser.add_argument("--agenda", action="append", default=[])
    args = parser.parse_args()

    agenda = args.agenda or [
        "Read the current Brain state and active blockers.",
        "Use the Brain decision as the authoritative objective.",
        "Review feasibility and safety without changing the objective.",
        "Return evidence and the next bounded action.",
        "Do not mark READY without verification evidence.",
    ]

    meeting = call(args.base, "/api/brain/council", "POST", {
        "title": args.title,
        "agenda": agenda,
    })
    if not meeting.get("ok", True):
        print(json.dumps({"ok": False, "stage": "COUNCIL", "result": meeting}, ensure_ascii=False))
        return 1

    meeting_id = meeting.get("meeting_id") or meeting.get("id")
    if meeting_id is None:
        print(json.dumps({"ok": False, "stage": "COUNCIL_ID", "result": meeting}, ensure_ascii=False))
        return 1

    execution = call(args.base, f"/api/brain/council/{int(meeting_id)}/execute", "POST", {})
    verification = call(args.base, f"/api/brain/council/{int(meeting_id)}/verify", "POST", {})

    result = {
        "ok": bool(verification.get("ok", False)),
        "authority": "BRAIN",
        "partner": "CHATGPT",
        "meeting_id": meeting_id,
        "execution": execution,
        "verification": verification,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
