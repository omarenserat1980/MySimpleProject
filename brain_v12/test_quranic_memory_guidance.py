from brain_v12.brain.quranic_core.memory_guidance import principles, review_memory


def test_principles_are_reference_linked_and_read_only():
    items = principles()
    assert items
    assert all(item["reference"] and item["theme"] for item in items)
    assert all("engineering_principle" in item for item in items)


def test_review_suggests_evidence_lens_without_claiming_truth():
    result = review_memory("هذا دليل يحتاج تحقق من المصدر")
    assert result["ok"] is True
    assert result["status"] == "REVIEW_SUGGESTIONS_ONLY"
    assert "evidence_and_verification" in result["matched_review_lenses"]
    assert result["matches"]
    assert any(item["reference"] == "2:260" for item in result["matches"])
    assert any("لا تُعدّل الذاكرة" in item for item in result["limitations"])


def test_review_empty_memory_fails_closed():
    result = review_memory("   ")
    assert result["ok"] is False
    assert result["status"] == "EMPTY_MEMORY"
    assert result["matches"] == []


def test_memory_evidence_preserves_source_confidence_and_timestamps(tmp_path):
    from brain_v12.brain.memory import MemoryStore

    store = MemoryStore(str(tmp_path / "brain.db"))
    store.init()
    store.save_memory("project:deployment", "Deployment must be verified against production.")
    first = store.add_memory_evidence(
        "project:deployment",
        "Production endpoint returned HTTP 200.",
        "runtime probe",
        0.95,
        observed_at="2026-10-11T03:00:00Z",
        metadata={"endpoint": "/health"},
    )
    assert first["source"] == "runtime probe"
    assert first["confidence"] == 0.95
    assert first["observed_at"] == "2026-10-11T03:00:00Z"
    assert first["recorded_at"]
    assert store.get_memory("project:deployment")["value"] == "Deployment must be verified against production."
    assert store.memory_evidence_conflicts("project:deployment")["status"] == "NO_CONFLICT_DETECTED"


def test_different_claims_for_same_memory_key_are_flagged_not_resolved(tmp_path):
    from brain_v12.brain.memory import MemoryStore

    store = MemoryStore(str(tmp_path / "brain.db"))
    store.init()
    store.save_memory("project:deployment", "Deployment status requires verification.")
    store.add_memory_evidence(
        "project:deployment", "Production health is HTTP 200.",
        "health probe", 0.9,
    )
    store.add_memory_evidence(
        "project:deployment", "Production health is HTTP 502.",
        "deployment log", 0.8,
    )
    result = store.memory_evidence_conflicts("project:deployment")
    assert result["status"] == "POTENTIAL_CONFLICT"
    assert len(result["groups"]) == 2
    assert "human/source verification" in result["message"]


def test_memory_evidence_rejects_invalid_confidence(tmp_path):
    import pytest
    from brain_v12.brain.memory import MemoryStore

    store = MemoryStore(str(tmp_path / "brain.db"))
    store.init()
    with pytest.raises(ValueError, match="OUT_OF_RANGE"):
        store.add_memory_evidence("k", "claim", "source", 1.1)
