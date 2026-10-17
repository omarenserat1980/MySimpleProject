from __future__ import annotations

from datetime import datetime, timezone
import json

from brain_v12.brain.braiins_pool_evidence_collector import (
    BRAIINS_WORKERS_URL,
    MAX_RESPONSE_BYTES,
    collect_braiins_pool_evidence,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, url=BRAIINS_WORKERS_URL, history=()):
        self.status_code = status_code
        self.url = url
        self.history = history
        self.content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        self._payload = payload

    def json(self):
        return self._payload

    def iter_bytes(self):
        yield self.content


class FakeClient:
    response = None
    init_kwargs = None
    request_args = None

    def __init__(self, **kwargs):
        type(self).init_kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    class _StreamContext:
        def __init__(self, response):
            self.response = response
        def __enter__(self):
            return self.response
        def __exit__(self, *_args):
            return False

    def stream(self, method, url, *, headers):
        type(self).request_args = (method, url, dict(headers))
        return self._StreamContext(type(self).response)


def fixture(now):
    return {"btc": {"workers": {"account.worker-01": {
        "state": "ok",
        "last_share": int(now.timestamp()) - 30,
        "hash_rate_unit": "Gh/s",
        "hash_rate_5m": 12.5,
        "hash_rate_60m": 11.5,
        "hash_rate_24h": 10.5,
        "shares_5m": 4,
        "shares_60m": 20,
        "shares_24h": 100,
    }}}}


def setup_response(now, **kwargs):
    FakeClient.response = FakeResponse(fixture(now), **kwargs)
    FakeClient.init_kwargs = None
    FakeClient.request_args = None


def test_collector_requires_existing_readonly_configuration_and_does_not_network():
    result = collect_braiins_pool_evidence(api_token="", expected_worker_id="account.worker-01",
                                           client_factory=FakeClient)
    assert result["reason"] == "READ_ONLY_POOL_API_TOKEN_NOT_CONFIGURED"
    assert result["network_access_performed"] is False
    assert FakeClient.request_args is None


def test_success_is_independent_pool_telemetry_not_brain_mining_or_revenue():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    setup_response(now)
    result = collect_braiins_pool_evidence(api_token="test-token-not-a-real-secret",
                                          expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["status"] == "TEST_FIXTURE_ONLY"
    assert result["pool_activity_verified"] is False
    assert result["evidence_origin"] == "INJECTED_TEST_FIXTURE"
    assert result["pool_source_authenticated_over_https"] is False
    assert result["accepted_share_submission_verified"] is False
    assert result["brain_runtime_activity_verified"] is False
    assert result["payout_verified"] is False
    assert result["revenue_verified"] is False
    assert result["pool_response_sha256"]
    assert result["proof_level"] == "SYNTHETIC_TEST_FIXTURE"
    assert FakeClient.init_kwargs == {"verify": True, "timeout": 10.0, "follow_redirects": False}
    assert FakeClient.request_args[0] == "GET"
    assert FakeClient.request_args[1] == BRAIINS_WORKERS_URL
    assert FakeClient.request_args[2] == {"Pool-Auth-Token": "test-token-not-a-real-secret"}
    assert "test-token-not-a-real-secret" not in json.dumps(result)


def test_wrong_worker_never_counts_as_pool_activity():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    setup_response(now)
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="other.worker",
                                          client_factory=FakeClient, now=now)
    assert result["reason"] == "EXPECTED_WORKER_NOT_FOUND_IN_POOL_RESPONSE"
    assert result["pool_activity_verified"] is False


def test_non_200_and_redirect_are_blocked():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    setup_response(now, status_code=401)
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["reason"] == "POOL_API_HTTP_STATUS_NOT_200"
    setup_response(now, history=(object(),))
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["reason"] == "UNEXPECTED_POOL_API_URL_OR_REDIRECT"


def test_stale_share_and_zero_shares_are_not_verified():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    payload = fixture(now)
    payload["btc"]["workers"]["account.worker-01"]["last_share"] = int(now.timestamp()) - 900
    FakeClient.response = FakeResponse(payload)
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["status"] == "BLOCKED_STALE_POOL_ACTIVITY"
    payload = fixture(now)
    payload["btc"]["workers"]["account.worker-01"]["shares_5m"] = 0
    FakeClient.response = FakeResponse(payload)
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["status"] == "POOL_ACTIVITY_NOT_ESTABLISHED"



def test_response_over_limit_is_rejected_during_streaming():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    setup_response(now)
    FakeClient.response.content = b"x" * (MAX_RESPONSE_BYTES + 1)
    result = collect_braiins_pool_evidence(
        api_token="test-token",
        expected_worker_id="account.worker-01",
        client_factory=FakeClient,
        now=now,
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "POOL_API_RESPONSE_SIZE_INVALID"
    assert result["network_access_performed"] is True

def test_nan_infinity_and_boolean_metrics_are_rejected():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    for bad in (float("nan"), float("inf"), True):
        payload = fixture(now)
        payload["btc"]["workers"]["account.worker-01"]["hash_rate_5m"] = bad
        FakeClient.response = FakeResponse(payload)
        result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                              client_factory=FakeClient, now=now)
        assert result["reason"] == "POOL_WORKER_METRICS_INVALID"
        assert result["pool_activity_verified"] is False


def test_wrong_origin_is_rejected():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    setup_response(now, url="https://attacker.example/accounts/workers/json/btc/")
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["reason"] == "UNEXPECTED_POOL_API_URL_OR_REDIRECT"
    assert result["pool_activity_verified"] is False


def test_unknown_hashrate_unit_is_rejected():
    now = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
    payload = fixture(now)
    payload["btc"]["workers"]["account.worker-01"]["hash_rate_unit"] = "widgets/s"
    FakeClient.response = FakeResponse(payload)
    result = collect_braiins_pool_evidence(api_token="test-token", expected_worker_id="account.worker-01",
                                          client_factory=FakeClient, now=now)
    assert result["reason"] == "POOL_WORKER_METRICS_INVALID"
    assert result["pool_activity_verified"] is False
