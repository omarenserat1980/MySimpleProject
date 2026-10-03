from decimal import Decimal
import pytest

from cloud.commercial_governance import (
    PriceInput, validate_price, validate_promotion, verify_payment,
    recognize_revenue, consent_allows,
)

def test_price_floor_and_target():
    p = PriceInput(Decimal("100"), operating_cost=Decimal("20"),
                   payment_cost=Decimal("5"), risk_reserve=Decimal("5"),
                   target_margin=Decimal("0.20"))
    assert p.floor() == Decimal("130")
    assert p.target_price() == Decimal("162.50")

def test_below_floor_requires_human_approval():
    p = PriceInput(Decimal("100"))
    with pytest.raises(ValueError):
        validate_price(Decimal("90"), p)
    validate_price(Decimal("90"), p, human_approval=True)

def test_promotion_requires_auditable_fields_and_approval():
    validate_promotion(reference_price=Decimal("100"), promotional_price=Decimal("80"),
                       start_date="2026-10-01", end_date="2026-10-31",
                       eligibility="new customers", approval=True)
    with pytest.raises(ValueError):
        validate_promotion(reference_price=Decimal("100"), promotional_price=Decimal("80"),
                           start_date="2026-10-01", end_date="2026-10-31",
                           eligibility="new customers", approval=False)

def test_payment_and_revenue_require_evidence():
    with pytest.raises(ValueError):
        verify_payment(invoice_id="INV-1", amount=Decimal("100"), currency="USD",
                       transaction_id="TX-1", evidence_ref="")
    verify_payment(invoice_id="INV-1", amount=Decimal("100"), currency="USD",
                   transaction_id="TX-1", evidence_ref="bank:abc")
    with pytest.raises(ValueError):
        recognize_revenue(payment_verified=False, delivered=True, evidence_ref="x")
    with pytest.raises(ValueError):
        recognize_revenue(payment_verified=True, delivered=False, payment_transaction_id="TX-1", payment_evidence_ref="bank:abc", delivery_evidence_ref="delivery:1", reconciliation_ref="recon:1")
    with pytest.raises(ValueError):
        recognize_revenue(payment_verified=True, delivered=True, payment_transaction_id="", payment_evidence_ref="bank:abc", delivery_evidence_ref="delivery:1", reconciliation_ref="recon:1")
    with pytest.raises(ValueError):
        recognize_revenue(payment_verified=True, delivered=True, payment_transaction_id="TX-1", payment_evidence_ref="bank:abc", delivery_evidence_ref="", reconciliation_ref="recon:1")
    recognize_revenue(payment_verified=True, delivered=True, payment_transaction_id="TX-1", payment_evidence_ref="bank:abc", delivery_evidence_ref="delivery:1", reconciliation_ref="recon:1")

def test_service_and_marketing_consent_are_separate():
    assert consent_allows(purpose="SERVICE", consents={"SERVICE": True, "MARKETING": False})
    assert not consent_allows(purpose="MARKETING", consents={"SERVICE": True, "MARKETING": False})
