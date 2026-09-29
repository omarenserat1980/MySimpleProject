from cloud.nafs_engine import NafsEngine, NafsState, QURAN_NAFS_REFERENCES

def test_quran_reference_registry_contains_core_states():
    refs={(r.surah,r.ayah) for r in QURAN_NAFS_REFERENCES}
    assert ("يوسف","12:53") in refs
    assert ("القيامة","75:2") in refs
    assert ("الفجر","89:27-30") in refs
    assert ("الشمس","91:7-10") in refs

def test_harmful_impulse_is_not_auto_executed():
    e=NafsEngine().assess("delete-production-data",benefit=.2,harm=.95,temptation=.9,uncertainty=.4,reversible=False)
    assert e.decision=="REJECT"

def test_uncertain_irreversible_action_is_deferred():
    e=NafsEngine().assess("publish-unverified-film",benefit=.8,harm=.4,temptation=.2,uncertainty=.95,reversible=False)
    assert e.decision in {"DEFER","REVIEW"}

def test_self_review_is_auditable():
    e=NafsEngine(); e.assess("run-qc",benefit=.7,harm=.05,uncertainty=.1)
    r=e.self_review()
    assert r["literal_human_soul_created"] is False
    assert r["history_count"]==1
