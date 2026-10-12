from datetime import datetime, timedelta, timezone

from economics.opportunity_verifier import verify_opportunity


def _now():
    return datetime.now(timezone.utc).isoformat()


def test_valid_jordan_remote_opportunity_passes():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan", "remote"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=_now(),
    )
    assert result.eligible
    assert result.reasons == ()
    assert result.confidence == 1.0
    assert len(result.source_fingerprint) == 64


def test_upfront_payment_fails_closed():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan"],
        upfront_cost_usd=5,
        source_url="https://example.com/job",
        last_verified_at=_now(),
    )
    assert not result.eligible
    assert "upfront_payment_required" in result.reasons
    assert result.confidence < 1.0


def test_stale_source_fails_closed():
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=old,
    )
    assert not result.eligible
    assert "stale_source" in result.reasons


def test_invalid_source_fails_closed():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan"],
        upfront_cost_usd=0,
        source_url="not-a-url",
        last_verified_at=_now(),
    )
    assert not result.eligible
    assert "invalid_source_url" in result.reasons


def test_wrong_region_fails_closed():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["US"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=_now(),
    )
    assert not result.eligible
    assert "region_not_eligible" in result.reasons


def test_future_timestamp_fails_closed():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=future,
    )
    assert not result.eligible
    assert "future_verification_timestamp" in result.reasons
