from brain_v12.brain.execution_evidence_bundle import build_evidence_bundle


def test_evidence_bundle_is_deterministic_and_does_not_claim_signature():
    args = ("task-1", "COMPLETED", "2026-10-10T12:00:00Z", {"exit_code": 0, "artifact": "out.bin"})
    first = build_evidence_bundle(*args)
    second = build_evidence_bundle(*args)
    assert first["sha256"] == second["sha256"]
    assert first["signature_verified"] is False
    assert first["execution_verified"] is False


def test_required_metadata_is_enforced():
    try:
        build_evidence_bundle("", "COMPLETED", "now", {})
    except ValueError as exc:
        assert str(exc) == "EVIDENCE_METADATA_REQUIRED"
    else:
        raise AssertionError("missing metadata accepted")
