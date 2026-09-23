from brain_v7.braincore_v2.research_engine import add_observation,verified_facts,snapshot
def test_research_requires_source(tmp_path,monkeypatch):
    import brain_v7.braincore_v2.research_engine as r
    monkeypatch.setattr(r,"PATH",tmp_path/"research.json")
    add_observation("finance","NPV formula verified","https://example.com",verified=True)
    assert len(verified_facts("finance"))==1
    assert snapshot()["observations"]==1
