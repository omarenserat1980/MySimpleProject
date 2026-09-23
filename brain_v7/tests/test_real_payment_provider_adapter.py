from brain_v7.braincore_v2.real_payment_provider_adapter import RealPaymentProviderAdapter


class Client:
    def __init__(self, response=None):
        self.response = response or {"status": "SUBMITTED", "provider_reference": "REF-1"}
        self.calls = []

    def submit_transfer(self, **kwargs):
        self.calls.append(("submit", kwargs))
        return self.response

    def get_transfer_status(self, **kwargs):
        self.calls.append(("status", kwargs))
        return {"status": "CONFIRMED", "amount_jod": 100.0}


def test_adapter_requires_external_authenticated_client():
    try:
        RealPaymentProviderAdapter(None)
    except ValueError as exc:
        assert str(exc) == "AUTHENTICATED_PROVIDER_CLIENT_REQUIRED"
    else:
        raise AssertionError("client must be required")


def test_adapter_submits_without_handling_secrets():
    client = Client()
    adapter = RealPaymentProviderAdapter(client)
    result = adapter.submit(100.0, "verified-destination", "IDEMP-1")
    assert result.status == "SUBMITTED"
    assert result.provider_reference == "REF-1"
    assert client.calls[0][1]["idempotency_key"] == "IDEMP-1"


def test_adapter_status_reads_provider_confirmation():
    client = Client()
    adapter = RealPaymentProviderAdapter(client)
    result = adapter.status("REF-1")
    assert result.status == "CONFIRMED"
    assert result.provider_reference == "REF-1"


def test_missing_provider_reference_fails_closed():
    client = Client({"status": "SUBMITTED"})
    adapter = RealPaymentProviderAdapter(client)
    result = adapter.submit(100.0, "verified-destination", "IDEMP-1")
    assert result.status == "FAILED"
    assert result.error_code == "PROVIDER_REFERENCE_MISSING"
