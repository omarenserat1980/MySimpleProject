import os
import pytest

from brain.provider_hub.paytabs_adapter import PayTabsAdapter, PayTabsConfig


def test_config_reads_secret_from_environment(monkeypatch):
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "186555")
    monkeypatch.setenv("PAYTABS_SERVER_KEY", "TEST_SECRET")
    cfg = PayTabsConfig.from_environment()
    assert cfg.profile_id == "186555"
    assert cfg.server_key == "TEST_SECRET"


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "186555")
    monkeypatch.delenv("PAYTABS_SERVER_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PAYTABS_SERVER_KEY_MISSING"):
        PayTabsConfig.from_environment()


def test_wrong_base_url_fails_closed(monkeypatch):
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "186555")
    monkeypatch.setenv("PAYTABS_SERVER_KEY", "TEST_SECRET")
    monkeypatch.setenv("PAYTABS_BASE_URL", "https://example.com")
    with pytest.raises(RuntimeError, match="PAYTABS_BASE_URL_NOT_ALLOWED"):
        PayTabsConfig.from_environment()


def test_payment_uses_server_secret_only_in_transport(monkeypatch):
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "186555")
    monkeypatch.setenv("PAYTABS_SERVER_KEY", "TEST_SECRET")
    seen = {}

    def transport(url, payload, headers):
        seen.update(url=url, payload=payload, headers=headers)
        return {"tran_ref": "T-TEST"}

    result = PayTabsAdapter(PayTabsConfig.from_environment(), transport).create_payment({
        "cart_id": "BRAIN-TEST-1",
        "cart_amount": 1,
        "cart_currency": "USD",
    })
    assert result["tran_ref"] == "T-TEST"
    assert seen["url"].endswith("/payment/request")
    assert seen["headers"]["Authorization"] == "TEST_SECRET"
    assert seen["payload"]["profile_id"] == 186555
