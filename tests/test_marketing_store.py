from brain_v12.marketing.marketing_engine import CampaignState, MarketingEngine
from brain_v12.marketing.marketing_store import CampaignStore


def test_campaign_survives_sqlite_round_trip(tmp_path):
    store = CampaignStore(tmp_path / "marketing.db")
    engine = MarketingEngine()
    campaign = engine.create_campaign(
        "Launch", "Generate qualified leads", "B2B", ["website", "youtube"], "Hello"
    )
    campaign.transition(CampaignState.REVIEW, "brain")
    store.save(campaign)

    restored = store.get(campaign.id)
    assert restored.id == campaign.id
    assert restored.state is CampaignState.REVIEW
    assert restored.channels == ["website", "youtube"]
    assert restored.events[-1]["to"] == "REVIEW"
    store.close()


def test_store_filters_by_state(tmp_path):
    store = CampaignStore(tmp_path / "marketing.db")
    engine = MarketingEngine()
    campaign = engine.create_campaign("A", "Test", "B2B", ["website"])
    store.save(campaign)
    assert [c.id for c in store.list(CampaignState.DRAFT)] == [campaign.id]
    assert store.list(CampaignState.PUBLISHED) == []
    store.close()
