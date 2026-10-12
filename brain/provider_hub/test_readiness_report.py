import json
from brain.provider_hub.commercial_gate import CommercialReadiness
from brain.provider_hub.readiness_report import build_report


def test_report_is_machine_readable(tmp_path):
    r = CommercialReadiness(
        True, True, True, True, False, False, False, True,
        "COMMERCIAL_LAUNCH_BLOCKED", ("PAYMENT_PROVIDER_NOT_ACTIVE",)
    )
    out = tmp_path / "commercial_readiness.json"
    result = build_report(r, out)
    saved = json.loads(out.read_text())
    assert saved["status"] == "COMMERCIAL_LAUNCH_BLOCKED"
    assert saved["checks"]["public_api"] is True
    assert "PAYMENT_PROVIDER_NOT_ACTIVE" in saved["blockers"]
    assert result == saved
