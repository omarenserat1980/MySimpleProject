# Brain State Snapshot

The utility `brain_v12/tools/brain_recovery_snapshot.py` creates a recovery-safe snapshot of runtime state without stopping Brain.

## Command

```bash
cd ~/MySimpleProject
python3 brain_v12/tools/brain_recovery_snapshot.py --output .brain/recovery/latest
```

## Captured when present

- Brain SQLite database from `BRAIN_DB` or the project default.
- Evidence SQLite database from `BRAIN_EVIDENCE_DB` or its default.
- Durable sync queue from `BRAIN_SYNC_QUEUE` or its default.
- Continuous supervisor history.

## Safety

- SQLite databases are copied using SQLite's backup API.
- API keys, control keys, OAuth tokens and agent key files are excluded.
- Device identity secrets are excluded.
- The live runtime is not stopped.
- Every copied file receives SHA-256 evidence.
- The manifest records the source Git commit.

## Recovery model

Source code is restored from the Golden checkpoint separately. State is restored only after its manifest and hashes are verified.

## Current limitation

A GitHub-hosted runner cannot see the live phone's private Termux filesystem. Therefore this utility must run on the actual Brain runtime host or a trusted self-hosted runtime runner to capture real production state. The current recovery workflow remains safe when no state files are present and does not claim that missing state was backed up.

This separation is intentional: source recovery and runtime-state recovery are two different layers.
