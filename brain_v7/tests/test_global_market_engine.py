from brain_v7.braincore_v2.global_market_engine import MarketSnapshot,compare_markets,market_unit_economics

def test_global_market_engine_does_not_invent_missing_data():
    s=MarketSnapshot("Jordan","JO","JOD","pump",observed_price=100)
    r=compare_markets([s])[0]
    assert r["verified_market_data"] is False
    assert "shipping_cost" in r["missing_fields"]

def test_market_unit_economics_requires_evidence():
    s=MarketSnapshot("EU","DE","EUR","pump",observed_price=150,shipping_cost=10,tariff_rate=.05)
    r=market_unit_economics(s,80)
    assert r["status"]=="CALCULATED"
    assert r["gross_profit"] < 150
