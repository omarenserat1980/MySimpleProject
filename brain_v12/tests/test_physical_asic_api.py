from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest

from brain_v12.brain import physical_asic_api as api


def _signed_report(key: str, challenge_id: str, nonce: str) -> dict:
    report = {
        "schema": "brain-physical-asic-attestation/v1",
        "device_id": "test-asic-01",
        "execution_mode": "PHYSICAL_DEVICE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "challenge_id": challenge_id,
        "challenge_nonce": nonce,
        "hashrate_mhs": 100.0,
        "elapsed_seconds": 60.0,
        "raw_response_sha256": "a" * 64,
        "physical_evidence": {"device_api_responded": True, "live_work_counters_present": True},
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    return {"report": report, "hmac_sha256": hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()}


def test_challenge_hmac_and_device_enrollment_gate(monkeypatch):
    key = "k" * 32
    monkeypatch.setenv("BRAIN_ASIC_HMAC_KEY", key)
    monkeypatch.setenv("BRAIN_ASIC_DEVICE_IDS", "test-asic-01")
    api._challenges.clear()
    api._seen_reports.clear()
    api._challenges["challenge-one"] = {"device_id": "test-asic-01", "nonce": "nonce-one", "created_at": __import__("time").time()}
    payload = _signed_report(key, "challenge-one", "nonce-one")
    result = api.verify_report(payload["report"], payload["hmac_sha256"])
    assert result["status"] == "PHYSICAL_DEVICE_API_CONNECTED"
    assert result["device_api_challenge_verified"] is True
    assert result["physical_silicon_provenance_verified"] is False
    assert result["revenue_verified"] is False


def test_bad_signature_rejected(monkeypatch):
    monkeypatch.setenv("BRAIN_ASIC_HMAC_KEY", "k" * 32)
    monkeypatch.setenv("BRAIN_ASIC_DEVICE_IDS", "test-asic-01")
    payload = _signed_report("k" * 32, "challenge-two", "nonce-two")
    with pytest.raises(ValueError, match="ASIC_HMAC_INVALID"):
        api.verify_report(payload["report"], "bad-signature")


def test_unknown_or_replayed_challenge_rejected(monkeypatch):
    monkeypatch.setenv("BRAIN_ASIC_HMAC_KEY", "k" * 32)
    monkeypatch.setenv("BRAIN_ASIC_DEVICE_IDS", "test-asic-01")
    payload = _signed_report("k" * 32, "missing-challenge", "nonce")
    with pytest.raises(ValueError, match="ASIC_CHALLENGE_UNKNOWN_OR_REPLAYED"):
        api.verify_report(payload["report"], payload["hmac_sha256"])


def test_unenrolled_device_rejected(monkeypatch):
    monkeypatch.setenv("BRAIN_ASIC_HMAC_KEY", "k" * 32)
    monkeypatch.setenv("BRAIN_ASIC_DEVICE_IDS", "another-device")
    payload = _signed_report("k" * 32, "x", "y")
    with pytest.raises(ValueError, match="ASIC_DEVICE_NOT_ENROLLED"):
        api.verify_report(payload["report"], payload["hmac_sha256"])
