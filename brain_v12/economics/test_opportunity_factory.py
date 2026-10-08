from datetime import datetime, timezone, timedelta

from economics.economic_memory import EconomicObservation, Outcome
from economics.opportunity_factory import (
    build_shortlist,
    deduplicate_records,
    is_stale,
)


def record(**overrides):
    value = {
        "opportunity_id": "job-1",
        "opportunity_class": "arabic_ai_evaluation",
        "expected_pay": 22,
        "acceptance_probability": 0.5,
        "brain_assistance": 0.8,
        "time_hours": 2,
        "entry_friction": 0.1,
        "risk": 0.1,
        "eligibility": ["Jordan", "remote"],
        "upfront_cost_usd": 0,
        "source_url": "https://example.com/jobs/1",
        "last_verified_at": "2026-10-08T00:00:00+00:00",
    }
    value.update(overrides)
    return value


def test_stale_gate():
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    old = (now - timedelta(days=31)).isoformat()
    assert is_stale(old, max_age_days=30, now=now)


def test_source_and_id_deduplication():
    records = [
        record(),
        record(opportunity_id="job-2"),
        record(opportunity_id="job-3", source_url="https://example.com/jobs/2"),
    ]
    result = deduplicate_records(records)
    assert [r["opportunity_id"] for r in result] == ["job-1", "job-3"]


def test_shortlist_is_read_only_and_keeps_verified_hold():
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    history = [
        EconomicObservation(
            opportunity_class="arabic_ai_evaluation",
            outcome=Outcome.ACCEPTED,
            hours_spent=1,
            advertised_pay=20,
        )
    ]
    result = build_shortlist([record()], observations=history, now=now)
    assert len(result) == 1
    assert result[0].verification.eligible
    assert result[0].decision.decision.value in {"HOLD", "PROCEED"}


def test_upfront_cost_is_not_shortlisted():
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    result = build_shortlist(
        [record(upfront_cost_usd=5)],
        now=now,
    )
    assert result == []
