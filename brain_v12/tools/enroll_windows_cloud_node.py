from __future__ import annotations

"""Issue a short-lived Brain Fabric enrollment token for a Windows Cloud VM.

The token is printed once to stdout. This tool never writes it to the
repository or to a source-controlled file.
"""

import argparse
import json
import os
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fabric-url", default=os.getenv("BRAIN_FABRIC_URL", "").rstrip("/"))
    p.add_argument("--node-id", default=os.getenv("BRAIN_WINDOWS_NODE_ID", ""))
    p.add_argument("--control-token", default=os.getenv("BRAIN_CONTROL_TOKEN", ""))
    p.add_argument("--ttl", type=int, default=900)
    args = p.parse_args()

    if not args.fabric_url or not args.node_id or not args.control_token:
        print(json.dumps({
            "ok": False,
            "status": "NOT_CONFIGURED",
            "reason": "BRAIN_FABRIC_URL_NODE_ID_OR_CONTROL_TOKEN_MISSING",
        }))
        return 2

    body = json.dumps({"node_id": args.node_id, "ttl_seconds": args.ttl}).encode()
    req = urllib.request.Request(
        f"{args.fabric_url}/v1/fabric/enroll",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + args.control_token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:
        print(json.dumps({"ok": False, "status": "ENROLLMENT_FAILED", "error": str(exc)[:300]}))
        return 1

    print(json.dumps({
        "ok": True,
        "status": "ENROLLMENT_ISSUED",
        "node_id": payload.get("node_id"),
        "expires_at": payload.get("expires_at"),
        "enrollment_token": payload.get("enrollment_token"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
