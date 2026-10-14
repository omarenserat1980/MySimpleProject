#!/usr/bin/env python3
"""Read-only bridge from a user-owned cgminer-compatible ASIC to Brain Cloud."""
from __future__ import annotations
import argparse, hashlib, hmac, ipaddress, json, os, socket, ssl, urllib.error, urllib.request
from datetime import datetime, timezone
from typing import Any

def validate_private_ipv4(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("ASIC_HOST_MUST_BE_LITERAL_IP") from exc
    if not isinstance(address, ipaddress.IPv4Address) or not address.is_private:
        raise ValueError("ASIC_HOST_MUST_BE_PRIVATE_IPV4")
    return str(address)

def parse_cgminer_response(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").replace("\x00", "").strip()
    if not text:
        raise ValueError("ASIC_EMPTY_RESPONSE")
    result: dict[str, Any] = {"sections": {}}
    for section in text.split("|"):
        section = section.strip()
        if not section:
            continue
        pieces = section.split(",")
        fields: dict[str, str] = {}
        for piece in pieces[1:]:
            if "=" in piece:
                key, value = piece.split("=", 1)
                fields[key.strip()] = value.strip()
        result["sections"][pieces[0].strip()] = fields
    status = result["sections"].get("STATUS", {})
    if status.get("Code") not in (None, "0", "S"):
        raise ValueError("ASIC_API_REPORTED_ERROR")
    if not result["sections"]:
        raise ValueError("ASIC_RESPONSE_UNPARSEABLE")
    return result

def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None

def build_attestation(parsed: dict[str, Any], device_id: str, observed_at: str | None = None) -> dict[str, Any]:
    sections = parsed.get("sections", {})
    summary = sections.get("SUMMARY", {})
    status = sections.get("STATUS", {})
    hashrate = _num(summary.get("MHS av") or summary.get("MHS 5s"))
    accepted = _num(summary.get("Accepted"))
    rejected = _num(summary.get("Rejected"))
    elapsed = _num(summary.get("Elapsed"))
    temperatures, fans, powers = [], [], []
    for values in sections.values():
        for key, value in values.items():
            low = key.lower()
            number = _num(value)
            if number is None:
                continue
            if "temp" in low and number <= 200:
                temperatures.append(number)
            if "fan" in low and ("rpm" in low or low.startswith("fan")):
                fans.append(number)
            if "power" in low or "watts" in low:
                powers.append(number)
    live = hashrate is not None and hashrate > 0 and accepted is not None and elapsed is not None and elapsed > 0
    return {
        "schema": "brain-physical-asic-attestation/v1",
        "device_id": device_id,
        "execution_mode": "PHYSICAL_DEVICE",
        "source_protocol": "cgminer-read-only-api",
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
        "api_status": status.get("Msg", "response_received"),
        "elapsed_seconds": elapsed,
        "hashrate_mhs": hashrate,
        "accepted_shares": accepted,
        "rejected_shares": rejected,
        "temperatures_c": temperatures,
        "fan_rpm": fans,
        "power_watts": powers,
        "raw_response_sha256": hashlib.sha256(json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "physical_evidence": {
            "device_api_responded": True,
            "live_work_counters_present": live,
            "verification_status": "LIVE_DEVICE_TELEMETRY" if live else "DEVICE_SEEN_UNVERIFIED",
            "physical_device_verified": False,
            "revenue_verified": False,
        },
        "limitations": [
            "Telemetry is not silicon provenance or proof of accepted pool shares.",
            "Brain must validate HMAC, freshness, enrollment, challenge and replay protection before assigning PHYSICAL_ASIC.",
        ],
    }

def read_cgminer(host: str, port: int, timeout: float) -> dict[str, Any]:
    host = validate_private_ipv4(host)
    if not 1 <= port <= 65535:
        raise ValueError("ASIC_PORT_OUT_OF_RANGE")
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(b"summary|devs|stats\x00")
        chunks, total = [], 0
        while total < 1024 * 1024:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if b"\x00" in chunk:
                break
    return parse_cgminer_response(b"".join(chunks))

def sign_report(report: dict[str, Any], key: str) -> str:
    if len(key.encode()) < 32:
        raise ValueError("BRAIN_ASIC_HMAC_KEY_MUST_BE_32_BYTES_MINIMUM")
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()

def post_report(url: str, report: dict[str, Any], key: str, timeout: float = 10) -> dict[str, Any]:
    if not url.startswith("https://"):
        raise ValueError("BRAIN_INGEST_REQUIRES_HTTPS")
    body = json.dumps({"report": report, "hmac_sha256": sign_report(report, key)}).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "Brain-Physical-ASIC-Agent/1"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            return {"http_status": response.status, "response": response.read(65536).decode("utf-8", errors="replace")}
    except urllib.error.URLError as exc:
        raise RuntimeError("BRAIN_INGEST_UNAVAILABLE") from exc

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("BRAIN_ASIC_HOST", ""))
    parser.add_argument("--port", type=int, default=int(os.getenv("BRAIN_ASIC_PORT", "4028")))
    parser.add_argument("--device-id", default=os.getenv("BRAIN_ASIC_DEVICE_ID", ""))
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--ingest-url", default=os.getenv("BRAIN_ASIC_INGEST_URL", ""))
    parser.add_argument("--hmac-key-env", default="BRAIN_ASIC_HMAC_KEY")
    args = parser.parse_args()
    if not args.host or not args.device_id:
        parser.error("--host and --device-id (or BRAIN_ASIC_HOST/BRAIN_ASIC_DEVICE_ID) are required")
    report = build_attestation(read_cgminer(args.host, args.port, args.timeout), args.device_id)
    key = os.getenv(args.hmac_key_env, "")
    if args.ingest_url:
        if not key:
            raise SystemExit("BRAIN_ASIC_HMAC_KEY_REQUIRED_FOR_CLOUD_INGEST")
        print(json.dumps({"report": report, "delivery": post_report(args.ingest_url, report, key)}, indent=2))
    else:
        print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
