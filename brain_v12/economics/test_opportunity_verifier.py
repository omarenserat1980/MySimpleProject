from datetime import datetime, timedelta, timezone

from economics.opportunity_verifier import verify_opportunity


def test_valid_jordan_remote_opportunity_passes():
    now = datetime.now(timezone.utc).isoformat()
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan", "remote"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=now,
    )
    assert result.eligible
    assert result.reasons == ()


def test_upfront_payment_fails_closed():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["Jordan"],
        upfront_cost_usd=5,
        source_url="https://example.com/job",
        last_verified_at=datetime.now(timezone.utc).isoformat(),
    )
    assert not result.eligible
    assert "upfront_payment_required" in result.reasons


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
        last_verified_at=datetime.now(timezone.utc).isoformat(),
    )
    assert not result.eligible
    assert "invalid_source_url" in result.reasons


def test_wrong_region_fails_closed():
    result = verify_opportunity(
        opportunity_id="x",
        eligibility=["US"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=datetime.now(timezone.utc).isoformat(),
    )
    assert not result.eligible
    assert "region_not_eligible" in result.reasons
