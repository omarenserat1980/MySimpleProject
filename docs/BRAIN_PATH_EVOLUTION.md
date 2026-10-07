# Brain Path Evolution

## Purpose

Brain keeps multiple execution, search, build, connectivity, and verification paths instead of relying on one hard-coded route.

Each path records:

- goal
- ordered steps
- run count
- success/failure count
- average execution time
- last failure
- evidence references
- computed score
- lifecycle status

## Selection policy

1. Prefer paths with repeated verified success.
2. Reliability dominates speed.
3. Use execution time to break ties between reliable paths.
4. Preserve failed paths as evidence; do not silently erase them.
5. When a path repeatedly fails, create or promote an alternative rather than looping indefinitely.
6. Keep one active orchestration path for a goal; parallel recovery loops are not allowed unless explicitly designed.
7. Every successful path should leave evidence that another run can reuse.

## Initial high-value paths

### PATH-BUILD-APK

source → Gradle CI → artifact → checksum → install → package verification

### PATH-TERMUX-BRAIN

Brain API → authenticated enqueue → redmi3-01 poll → execution → report → verification

### PATH-ANDROID-EXECUTOR

APK → android-executor-redmi3-01 → Brain poll → real task → result → verification

### PATH-FAST-SCAN

GitHub state → active CI → runtime health → device status → only then deep inspection

### PATH-FAST-RECOVERY

failure evidence → classify blocker → choose highest-scoring alternative → execute one repair → verify → record outcome

## Evolution rule

The system must improve from evidence, not from repeated guessing.

A path becomes **proven** after at least two successful recorded runs. A path may remain **degraded** when failures exist, but it remains available as historical evidence.

Registry implementation:

`brain_v12/brain/path_evolution.py`

Default runtime state:

`.brain/state/path_evolution.json`

The registry is local runtime state and must not contain secrets.
