from brain_v7.braincore_v2.live_opportunity_sources import (
    build_research_queue,
    normalize_search_result,
    source_registry,
)


def test_registry_contains_multiple_sources():
    assert len(source_registry()) >= 4


def test_fresh_result_is_accepted():
    row = normalize_search_result({
        "source": "Upwork",
        "title": "Arabic short video",
        "url": "https://www.upwork.com/example",
        "publish_date": "2026-09-22",
        "excerpts": ["remote freelance"],
    })
    assert row["evidence_status"] == "FRESH"


def test_unknown_date_needs_verification():
    row = normalize_search_result({
        "source": "Freelancer",
        "title": "Arabic copywriter",
        "url": "https://www.freelancer.com/example",
    })
    assert row["evidence_status"] == "NEEDS_DATE_VERIFICATION"


def test_unknown_source_rejected():
    assert normalize_search_result({
        "source": "Unknown",
        "title": "x",
        "url": "https://example.com/x",
    }) is None


def test_queue_never_enables_submission():
    queue = build_research_queue([])
    assert queue["execution_enabled"] is False
    assert queue["submission_requires_user_action"] is True
