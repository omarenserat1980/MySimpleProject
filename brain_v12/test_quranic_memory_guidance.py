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


def test_authenticated_endpoint_reviews_actual_stored_memory_and_evidence(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from brain_v12.brain.memory import MemoryStore
    from brain_v12.brain.quranic_core.api import build_router

    store = MemoryStore(str(tmp_path / "brain.db"))
    store.init()
    store.save_memory("review-key", "هذا دليل يحتاج تحقق من المصدر")
    store.add_memory_evidence(
        "review-key", "Source was checked.", "test fixture", 0.9,
        observed_at="2026-10-11T04:00:00Z",
    )
    app = FastAPI()
    app.include_router(build_router(memory_store=store))
    monkeypatch.setenv("BRAIN_CONTROL_KEY", "test-control-secret")

    response = TestClient(app).post(
        "/api/quranic-core/memory-guidance/review-stored",
        headers={"X-Brain-Control-Key": "test-control-secret"},
        json={"memory_key": "review-key"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["memory_key"] == "review-key"
    assert result["memory_updated_at"]
    assert result["evidence"][0]["source"] == "test fixture"
    assert result["evidence"][0]["confidence"] == 0.9
    assert result["memory_mutated"] is False
    assert "evidence_and_verification" in result["matched_review_lenses"]


def test_stored_memory_review_rejects_missing_control_key(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from brain_v12.brain.memory import MemoryStore
    from brain_v12.brain.quranic_core.api import build_router

    store = MemoryStore(str(tmp_path / "brain.db"))
    store.init()
    store.save_memory("private-key", "Sensitive memory with source details.")
    app = FastAPI()
    app.include_router(build_router(memory_store=store))
    monkeypatch.setenv("BRAIN_CONTROL_KEY", "test-control-secret")

    response = TestClient(app).post(
        "/api/quranic-core/memory-guidance/review-stored",
        json={"memory_key": "private-key"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CONTROL_PLANE_AUTH_REQUIRED"
