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
