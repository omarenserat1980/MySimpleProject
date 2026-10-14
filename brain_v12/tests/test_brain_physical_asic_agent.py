from __future__ import annotations
import hashlib, hmac, json
import pytest
from tools.brain_physical_asic_agent import build_attestation, parse_cgminer_response, sign_report, validate_private_ipv4

def test_private_ipv4_only_and_no_hostname():
    assert validate_private_ipv4("192.168.1.10") == "192.168.1.10"
    with pytest.raises(ValueError, match="ASIC_HOST_MUST_BE_LITERAL_IP"):
        validate_private_ipv4("miner.local")
    with pytest.raises(ValueError, match="ASIC_HOST_MUST_BE_PRIVATE_IPV4"):
        validate_private_ipv4("8.8.8.8")

def test_parse_and_attest_live_telemetry():
    raw = (b"STATUS=S,When=1730000000,Code=0,Msg=Summary,Description=cgminer|"
           b"SUMMARY,Elapsed=3600,MHS av=120000000,Accepted=12,Rejected=1|"
           b"STATS,ID=ASIC 0,Temperature=62,fan1=4200,Power=3000|\x00")
    report = build_attestation(parse_cgminer_response(raw), "brain-asic-lab-01")
    assert report["execution_mode"] == "PHYSICAL_DEVICE"
    assert report["hashrate_mhs"] == 120000000
    assert report["accepted_shares"] == 12
    assert report["rejected_shares"] == 1
    assert report["physical_evidence"]["verification_status"] == "LIVE_DEVICE_TELEMETRY"
    assert report["physical_evidence"]["physical_device_verified"] is False
    assert report["physical_evidence"]["revenue_verified"] is False

def test_empty_or_error_response_rejected():
    with pytest.raises(ValueError, match="ASIC_EMPTY_RESPONSE"):
        parse_cgminer_response(b"\x00")
    with pytest.raises(ValueError, match="ASIC_API_REPORTED_ERROR"):
        parse_cgminer_response(b"STATUS=E,When=1,Code=17,Msg=Access denied|\x00")

def test_report_hmac_is_deterministic_and_requires_long_key():
    report = {"device_id": "test", "hashrate_mhs": 12}
    key = "k" * 32
    expected = hmac.new(key.encode(), json.dumps(report, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    assert sign_report(report, key) == expected
    with pytest.raises(ValueError, match="BRAIN_ASIC_HMAC_KEY_MUST_BE_32_BYTES_MINIMUM"):
        sign_report(report, "short")
