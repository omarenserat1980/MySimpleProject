import hashlib
import hmac
import json

from brain.provider_hub.paytabs_evidence_bridge import PayTabsEvidenceBridge


def test_verified_callback_becomes_payment_evidence():
    key = "TEST_SECRET"
    payload = {
        "cart_id": "BRAIN-TEST-2",
        "cart_total": "1.00",
        "cart_currency": "USD",
        "response_status": "A",
        "tran_ref": "TST456",
        "transaction_time": "2026-10-04T20:00:00Z",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
    result = PayTabsEvidenceBridge(key).verify_callback(
        raw, signature,
        order_id="BRAIN-TEST-2",
        amount="1.00",
        currency="USD",
    )
    assert result.transaction_ref == "TST456"
    assert result.evidence.source == "paytabs"
    assert result.evidence.evidence_type == "PAYMENT_VERIFICATION"
