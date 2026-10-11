from brain_v12.brain.quranic_core.memory_guidance import principles, review_memory


def test_principles_are_source_linked():
    items = principles()
    assert items
    assert all(item["reference"] and item["theme"] and item["engineering_principle"] for item in items)


def test_evidence_review_is_suggestion_only():
    result = review_memory("هذا دليل يحتاج تحقق من المصدر")
    assert result["ok"] is True
    assert result["status"] == "REVIEW_SUGGESTIONS_ONLY"
    assert "evidence_and_verification" in result["matched_review_lenses"]
    assert result["memory_mutated"] is False


def test_empty_input_fails_closed():
    result = review_memory("  ")
    assert result["ok"] is False
    assert result["status"] == "EMPTY_MEMORY"
    assert result["matches"] == []


def test_uncertainty_and_counterevidence_are_detected_without_mutation():
    result = review_memory("This assumption is uncertain; check counterevidence.")
    assert result["ok"] is True
    assert "uncertainty_and_doubt" in result["matched_review_lenses"]
    assert "humility_and_counterevidence" in result["matched_review_lenses"]
    assert result["memory_mutated"] is False


def test_quranic_core_router_exposes_read_only_guidance():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from brain_v12.brain.quranic_core.api import build_router

    app = FastAPI()
    app.include_router(build_router())
    client = TestClient(app)

    guidance = client.get("/api/quranic-core/memory-guidance")
    assert guidance.status_code == 200
    assert guidance.json()["memory_mutated"] is False
    assert guidance.json()["count"] > 0

    review = client.post(
        "/api/quranic-core/memory-guidance/review",
        json={"memory_text": "هذا دليل يحتاج تحقق من المصدر"},
    )
    assert review.status_code == 200
    assert review.json()["memory_mutated"] is False
    assert "evidence_and_verification" in review.json()["matched_review_lenses"]
