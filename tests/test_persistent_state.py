from __future__ import annotations

from pathlib import Path

from platform_foundation.persistent_state import SQLiteStateStore


def test_state_survives_reopen(tmp_path: Path) -> None:
    db = tmp_path / "state.sqlite3"
    first = SQLiteStateStore(db)
    first.set("job", {"status": "SUCCESS", "attempt": 1})
    first.close()

    second = SQLiteStateStore(db)
    assert second.get("job") == {"status": "SUCCESS", "attempt": 1}
    assert second.is_ready()
    second.close()


def test_restore_replaces_state(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.sqlite3")
    store.set("old", 1)
    store.restore({"new": [1, 2, 3]})
    assert store.snapshot() == {"new": [1, 2, 3]}
    store.close()


def test_missing_key_uses_default(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state.sqlite3")
    assert store.get("missing", "fallback") == "fallback"
    store.close()
