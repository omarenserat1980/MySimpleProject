import time

import pytest

from platform_foundation.memory import MemoryEngine, MemoryKind
from platform_foundation.persistent_state import SQLiteStateStore


def test_memory_persists_and_updates_without_duplicate_active_key(tmp_path):
    path = tmp_path / "memory.db"
    first = SQLiteStateStore(str(path))
    memory = MemoryEngine(first)
    created = memory.remember(
        kind=MemoryKind.FACT,
        key="brain.name",
        value="Electronic Brain",
        source="verified-test",
        confidence=0.9,
    )
    updated = memory.remember(
        kind=MemoryKind.FACT,
        key="brain.name",
        value="Electronic Brain v2",
        source="verified-test",
        confidence=1.0,
    )
    assert updated.memory_id == created.memory_id
    first.close()

    second = SQLiteStateStore(str(path))
    records = MemoryEngine(second).list(kind=MemoryKind.FACT)
    second.close()
    assert len(records) == 1
    assert records[0].value == "Electronic Brain v2"
    assert records[0].confidence == 1.0


def test_memory_categories_are_typed_and_isolated(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "memory.db"))
    memory = MemoryEngine(store)
    memory.remember(kind=MemoryKind.PREFERENCE, key="delivery", value="concise", source="user", confidence=1.0)
    memory.remember(kind=MemoryKind.DECISION, key="render.provider", value="free-first", source="decision", confidence=0.95)
    assert memory.get(kind=MemoryKind.PREFERENCE, key="delivery").value == "concise"
    assert memory.get(kind=MemoryKind.DECISION, key="delivery") is None
    store.close()


def test_memory_requires_provenance_and_valid_confidence(tmp_path):
    memory = MemoryEngine(SQLiteStateStore(str(tmp_path / "memory.db")))
    with pytest.raises(ValueError):
        memory.remember(kind=MemoryKind.FACT, key="x", value=1, source="", confidence=1.0)
    with pytest.raises(ValueError):
        memory.remember(kind=MemoryKind.FACT, key="x", value=1, source="test", confidence=1.1)


def test_temporary_memory_expires_and_can_be_forgotten(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "memory.db"))
    memory = MemoryEngine(store)
    record = memory.remember(
        kind=MemoryKind.TEMPORARY_STATE,
        key="session",
        value={"active": True},
        source="runtime",
        expires_at=time.time() - 1,
    )
    assert memory.get(kind=MemoryKind.TEMPORARY_STATE, key="session") is None
    assert memory.get(kind=MemoryKind.TEMPORARY_STATE, key="session", include_expired=True).memory_id == record.memory_id

    active = memory.remember(kind=MemoryKind.FACT, key="forget.me", value=True, source="test")
    assert memory.forget(active.memory_id) is True
    assert memory.get(kind=MemoryKind.FACT, key="forget.me") is None
    assert memory.forget(active.memory_id) is False
    store.close()
