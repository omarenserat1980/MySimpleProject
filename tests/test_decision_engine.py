from platform_foundation.decision_engine import DecisionEngine, DecisionOption, DecisionRisk
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.memory import MemoryEngine, MemoryKind
import pytest


def test_decision_selects_best_evidenced_option_and_persists(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "decision.db"))
    engine = DecisionEngine(store)
    record = engine.decide(
        subject="media.provider",
        options=[
            DecisionOption("free-local", 0.92, "no upfront cost"),
            DecisionOption("paid-api", 0.70, "faster but costs money"),
        ],
        risk=DecisionRisk.MEDIUM,
        confidence=0.95,
        evidence=["ci:verified", "cost:zero"],
    )
    assert record.selected == "free-local"
    assert record.alternatives[0].option == "paid-api"
    assert engine.get(record.decision_id) == record
    assert MemoryEngine(store).get(kind=MemoryKind.DECISION, key="media.provider") is not None
    store.close()


def test_decision_requires_evidence_and_valid_confidence(tmp_path):
    engine = DecisionEngine(SQLiteStateStore(str(tmp_path / "decision.db")))
    with pytest.raises(ValueError):
        engine.decide(subject="x", options=[DecisionOption("a", 1, "x")], risk=DecisionRisk.LOW, confidence=1, evidence=[])
    with pytest.raises(ValueError):
        engine.decide(subject="x", options=[DecisionOption("a", 1, "x")], risk=DecisionRisk.LOW, confidence=1.1, evidence=["e"])


def test_irreversible_decision_requires_high_confidence_and_non_reversible_flag(tmp_path):
    engine = DecisionEngine(SQLiteStateStore(str(tmp_path / "decision.db")))
    option=[DecisionOption("commit", 1, "verified")]
    with pytest.raises(ValueError):
        engine.decide(subject="x", options=option, risk=DecisionRisk.IRREVERSIBLE, confidence=0.8, evidence=["e"], reversible=False)
    with pytest.raises(ValueError):
        engine.decide(subject="x", options=option, risk=DecisionRisk.IRREVERSIBLE, confidence=0.95, evidence=["e"], reversible=True)
