# BRAIN-ASIC-001 SQLite identity memory

The identity record is persisted locally in SQLite so Brain can retrieve it across restarts without relying on chat history.

## Default database

- Default path: `.brain/asic_identity.sqlite3` under the repository root.
- Override path with environment variable `BRAIN_ASIC_DB` or CLI option `--db /absolute/path/identity.sqlite3`.
- The database is created locally when initialized. Do not commit runtime database files or store credentials, pool passwords, API tokens, or private keys in it.

## Commands

Run from the repository root:

```bash
# Initialize the database and show readiness
python -m brain_v12.asic.unit_001.sqlite_identity_store init

# Save known facts from a local JSON file (unknown values remain unknown)
python -m brain_v12.asic.unit_001.sqlite_identity_store save --input /path/to/asic-001-identity.json

# Retrieve the canonical BRAIN-ASIC-001 record
python -m brain_v12.asic.unit_001.sqlite_identity_store get

# List all registered ASIC identity records
python -m brain_v12.asic.unit_001.sqlite_identity_store list

# Check database health
python -m brain_v12.asic.unit_001.sqlite_identity_store health
```

Example using an alternate database path:

```bash
python -m brain_v12.asic.unit_001.sqlite_identity_store --db /data/brain-asic.sqlite3 init
```

## Persistence contract

- One current record per Brain product ID; saving the same ID updates the record.
- The original facts, connection metadata, evidence references, and verification status are stored as JSON plus queryable status columns.
- The store does not scan for hardware, contact mining pools, or launch mining.
- Boolean claims alone cannot establish physical identity or live mining. The identity registry requires evidence references for each verification gate.
- An empty record is valid and remains `IDENTIFICATION_INCOMPLETE`; the system never invents a chip model, serial number, hashrate, or revenue.

## Tests

```bash
python -m unittest brain_v12.asic.unit_001.test_identity_registry brain_v12.asic.unit_001.test_sqlite_identity_store
```
