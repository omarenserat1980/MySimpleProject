from pathlib import Path
from brain_v12.brain.industrial_quote_portal import InquiryIn, InquiryStore

def test_create_inquiry_persists_and_generates_id(tmp_path: Path):
    store = InquiryStore(str(tmp_path / "inquiries.json"))
    body = InquiryIn(
        company="Test Industrial",
        contact_name="A User",
        email="buyer@example.com",
        category="Hydraulics",
        message="Please send availability and a quote for this item.",
    )
    item = store.create(body)
    assert item["id"].startswith("Q-")
    assert item["status"] == "NEW"
    loaded = store.all()
    assert len(loaded) == 1
    assert loaded[0]["id"] == item["id"]

def test_store_recovers_from_missing_file(tmp_path: Path):
    store = InquiryStore(str(tmp_path / "missing.json"))
    assert store.all() == []
