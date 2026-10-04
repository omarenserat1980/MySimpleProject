from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence
from brain.provider_hub.lifecycle import ProviderRecord
from brain.provider_hub.commercial_gate import evaluate


def test_gate_reports_blocked_without_real_prerequisites():
    g = CommercialEvidenceGate()
    p = ProviderRecord("payment", "payment", 1, "DISCOVERED")
    result = evaluate(
        public_api=False,
        auth_verified=True,
        trial_enforced=True,
        order_flow_verified=True,
        payment_provider=p,
        payment_verification_live=False,
        delivery_verified=False,
        evidence_gate=g,
        order_id="o1",
    )
    assert result.status == "COMMERCIAL_LAUNCH_BLOCKED"
    assert "PUBLIC_API_NOT_VERIFIED" in result.blockers


def test_gate_can_report_ready_when_all_facts_are_present():
    g = CommercialEvidenceGate()
    p = ProviderRecord("payment", "payment", 1, "ACTIVE")
    g.add(Evidence.create("pay", "PAYMENT_VERIFICATION", "o1", "verified-test", "p1", {"ok": True}))
    g.add(Evidence.create("rev", "REVENUE_CONFIRMATION", "o1", "verified-test", "r1", {"ok": True}))
    result = evaluate(
        public_api=True,
        auth_verified=True,
        trial_enforced=True,
        order_flow_verified=True,
        payment_provider=p,
        payment_verification_live=True,
        delivery_verified=True,
        evidence_gate=g,
        order_id="o1",
    )
    assert result.status == "COMMERCIAL_READY"
