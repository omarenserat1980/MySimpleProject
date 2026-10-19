# SQLite experiment memory

Electronic Brain already has SQLite-backed stores for specific domains (including ASIC identity). This module adds a separate append-only history for test runs and evidence so prior work can be retrieved after a process restart rather than reconstructed from chat.

## Usage

```python
from brain_v12.asic.unit_001.sqlite_evidence_store import ExperimentMemory

memory = ExperimentMemory(".brain/experiment_memory.sqlite3")
memory.init()
event = memory.record({
    "project": "Electronic Brain",
    "subject": "realme-rmx3710",
    "event_type": "sha256d_reference_test",
    "status": "PASS",
    "environment": {"os": "Android 15", "arch": "aarch64", "python": "3.13.13"},
    "measurements": {"iterations": 10000, "sha256d_operations_per_second": 203864.97},
    "evidence": ["Bitcoin genesis-header SHA-256d reference vector matched"],
    "limitations": ["not mining evidence", "not ASIC-equivalent performance", "power not measured"]
})
print(memory.list_events(subject="realme-rmx3710"))
```

The example measurements above record one observed run and are not a performance guarantee. Prefer appending each new run as a new event rather than overwriting history. Do not persist credentials, tokens, private keys, or secrets. Runtime database files belong in `.brain/` and must not be committed.

## Scope

This is local SQLite persistence, not automatic cross-device synchronization. To share history between the phone and Brain Cloud, a separately authenticated sync/replication path must be designed. A successful software test must never be interpreted as proof of physical ASIC hardware, pool-accepted shares, or realized revenue.

## Tests

```bash
python -m unittest brain_v12.asic.unit_001.test_sqlite_evidence_store
```
