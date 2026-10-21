"""Non-authorizing Stratum V1 handshake probe for Solo CKPool.

Sends only ``mining.subscribe``. It never authorizes a worker, submits shares,
starts a miner, or treats a subscription response as mining/revenue evidence.
"""
from __future__ import annotations

import json
import socket
import time
from typing import Any


def probe_ckpool_stratum(
    host: str = "stratum.ckpool.org",
    port: int = 3333,
    *,
    timeout: float = 6.0,
    socket_factory=socket.create_connection,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "electronic-brain.ckpool-stratum-probe.v1",
        "host": host,
        "port": port,
        "probe": "mining.subscribe only",
        "authorization_sent": False,
        "share_submission_sent": False,
        "mining_started": False,
        "revenue_realized": False,
    }
    request = {"id": 1, "method": "mining.subscribe", "params": ["ElectronicBrain-readonly-probe/1.0"]}
    try:
        started = time.monotonic()
        with socket_factory((host, port), timeout=timeout) as connection:
            connection.settimeout(timeout)
            connection.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
            buffer = b""
            while b"\n" not in buffer and len(buffer) < 16384:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                buffer += chunk
        report["tcp_connected"] = True
        report["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
        line = buffer.split(b"\n", 1)[0].decode("utf-8", "replace").strip()
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            report["jsonrpc_response"] = False
            report["response_preview"] = line[:240]
            return report
        report["jsonrpc_response"] = isinstance(message, dict) and message.get("id") == 1
        report["error_present"] = bool(message.get("error")) if isinstance(message, dict) else True
        result = message.get("result") if isinstance(message, dict) else None
        report["subscription_response_present"] = isinstance(result, list) and bool(result)
        if isinstance(result, list):
            report["subscription_result_items"] = len(result)
    except (OSError, TimeoutError, ValueError) as exc:
        report["tcp_connected"] = False
        report["error_type"] = type(exc).__name__
    report["evidence_limit"] = (
        "A successful subscribe response proves only Stratum protocol reachability. "
        "No worker authorization, share submission, local mining, block, or revenue was tested."
    )
    return report


if __name__ == "__main__":
    print(json.dumps(probe_ckpool_stratum(), indent=2, sort_keys=True))
