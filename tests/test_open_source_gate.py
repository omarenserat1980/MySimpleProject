from platform_foundation.open_source_gate import (
    OpenSourceCandidate,
    OpenSourceDecision,
    OpenSourceGate,
)


def test_complete_candidate_is_approved():
    result = OpenSourceGate().evaluate(
        OpenSourceCandidate(
            "example", "global", "Apache-2.0", "1.0.0",
            True, True, True, True,
        )
    )
    assert result.decision is OpenSourceDecision.APPROVED
    assert result.reasons == ()


def test_missing_security_blocks():
    result = OpenSourceGate().evaluate(
        OpenSourceCandidate(
            "example", "china", "Apache-2.0", "1.0.0",
            True, False, True, True,
        )
    )
    assert result.decision is OpenSourceDecision.BLOCKED
    assert "security_review_missing" in result.reasons


def test_unpinned_version_and_external_runtime_block():
    result = OpenSourceGate().evaluate(
        OpenSourceCandidate(
            "example", "india", "MIT", "",
            False, True, True, True,
        )
    )
    assert result.decision is OpenSourceDecision.BLOCKED
    assert "version_not_pinned" in result.reasons
    assert "self_hosting_not_proven" in result.reasons
