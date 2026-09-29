from cloud.quran_nafs_corpus import NAFS_CORPUS, corpus_stats

def test_corpus_has_core_nafs_states():
    refs={v.ref for v in NAFS_CORPUS}
    assert {"12:53","75:2","89:27-30","91:7-10"}.issubset(refs)

def test_corpus_has_accountability_uncertainty_recovery():
    refs={v.ref for v in NAFS_CORPUS}
    assert {"6:164","31:34","39:53","59:18"}.issubset(refs)

def test_corpus_is_nonempty_and_auditable():
    stats=corpus_stats()
    assert stats["verses"] >= 30
    assert stats["source_scope"].startswith("Quranic references")
