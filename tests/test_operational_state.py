from platform_foundation.operational_state import OperationalStateStore
from platform_foundation.persistent_state import SQLiteStateStore


def test_operational_state_persists_across_store_restart(tmp_path):
    path = tmp_path / "state.db"

    first = SQLiteStateStore(str(path))
    state1 = OperationalStateStore(first).set(phase="3_OPERATIONAL", status="READY")
    first.close()

    second = SQLiteStateStore(str(path))
    state2 = OperationalStateStore(second).get()
    second.close()

    assert state2 == state1
    assert state2.revision == 1


def test_operational_state_revision_is_monotonic(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    state = OperationalStateStore(store)
    first = state.set(phase="3_OPERATIONAL", status="STARTING")
    second = state.set(phase="3_OPERATIONAL", status="READY")
    store.close()

    assert second.revision == first.revision + 1
