from brain.provider_hub.contracts import AdapterRegistry, HealthResult


class FakeAdapter:
    provider_id = "fake"

    def health_check(self):
        return HealthResult("fake", True, "test", {"source": "unit-test"})

    def create_checkout(self, order_id, amount, currency):
        raise NotImplementedError

    def verify_payment(self, provider_reference):
        raise NotImplementedError


def test_registry_register_and_health():
    r = AdapterRegistry()
    r.register(FakeAdapter())
    result = r.health()
    assert len(result) == 1
    assert result[0].healthy is True
    assert result[0].evidence["source"] == "unit-test"


def test_registry_rejects_duplicate():
    r = AdapterRegistry()
    r.register(FakeAdapter())
    try:
        r.register(FakeAdapter())
    except ValueError as e:
        assert str(e) == "DUPLICATE_PROVIDER:fake"
    else:
        raise AssertionError("duplicate provider accepted")
