import hashlib
import hmac
import json

import pytest

from brain.provider_hub.paytabs_webhook import verify_ipn_signature, parse_and_validate_payment


KEY = "TEST_SECRET"


def body():
    return json.dumps({
        "cart_id": "BRAIN-TEST-1",
        "cart_amount": "1.00",
        "cart_currency": "USD",
        "payment_result": {"response_status": "A"},
        "tran_ref": "TST123",
    }, separators=(",", ":")).encode()


def signature(raw):
    return hmac.new(KEY.encode(), raw, hashlib.sha256).hexdigest()


def test_valid_signature():
    raw = body()
    assert verify_ipn_signature(raw, signature(raw), KEY)


def test_tampered_body_is_rejected():
    raw = body()
    assert not verify_ipn_signature(raw + b"tampered", signature(raw), KEY)


def test_valid_payment_payload():
    raw = body()
    result = parse_and_validate_payment(
        raw, signature(raw), KEY,
        expected_order_id="BRAIN-TEST-1",
        expected_amount="1.00",
        expected_currency="USD",
    )
    assert result["tran_ref"] == "TST123"


@pytest.mark.parametrize("field,value,error", [
    ("cart_id", "WRONG", "PAYTABS_ORDER_MISMATCH"),
    ("cart_amount", "99.00", "PAYTABS_AMOUNT_MISMATCH"),
    ("cart_currency", "JOD", "PAYTABS_CURRENCY_MISMATCH"),
])
def test_top_level_mismatches_are_rejected(field, value, error):
    data = json.loads(body())
    data[field] = value
    raw = json.dumps(data, separators=(",", ":")).encode()
    with pytest.raises(ValueError, match=error):
        parse_and_validate_payment(
            raw, signature(raw), KEY,
            expected_order_id="BRAIN-TEST-1",
            expected_amount="1.00",
            expected_currency="USD",
        )


def test_unauthorised_payment_is_rejected():
    data = json.loads(body())
    data["payment_result"]["response_status"] = "E"
    raw = json.dumps(data, separators=(",", ":")).encode()
    with pytest.raises(ValueError, match="PAYTABS_PAYMENT_NOT_AUTHORISED"):
        parse_and_validate_payment(
            raw, signature(raw), KEY,
            expected_order_id="BRAIN-TEST-1",
            expected_amount="1.00",
            expected_currency="USD",
        )


def test_missing_transaction_reference_is_rejected():
    data = json.loads(body())
    data.pop("tran_ref")
    raw = json.dumps(data, separators=(",", ":")).encode()
    with pytest.raises(ValueError, match="PAYTABS_TRANSACTION_REFERENCE_MISSING"):
        parse_and_validate_payment(
            raw, signature(raw), KEY,
            expected_order_id="BRAIN-TEST-1",
            expected_amount="1.00",
            expected_currency="USD",
        )
