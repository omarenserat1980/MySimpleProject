# Base Expansion V2 — Baseline

## Status
BASE_EXPANSION = IN_PROGRESS
PHASE = 0_BASELINE_AND_BOUNDARIES
SOURCE_OF_TRUTH = GitHub/main

## Repository reality
The repository is already a substantial Electronic Brain V12 system. It is not an empty repository and must not be treated as one.

Observed on 2026-10-05:
- Default branch: main
- Brain V12 package: brain_v12/
- Brain core modules: brain_v12/brain/
- Business modules: brain_v12/business/
- Brain Git platform: brain_v12/brain_git/
- CI/workflow estate: .github/workflows/
- Tests: tests/ plus package-level tests
- Device/emulator tooling: tools/, termux_agent/, v12-agent/
- Existing web/game/marketing surfaces are present.

## Existing evidence observed
verification/latest.json reports PASS for its recorded verification set, including 53 Brain V12 tests in the captured run. This is historical evidence for those checks, not proof that the new Base Expansion is verified.

## Reuse policy
Existing Brain capabilities remain preserved. The new foundation must be independent of Brain during its initial build and verification.

## Initial scope
Build a minimal, real, independently testable foundation first. Expand only after its gates pass.

## Deferred by design
Full search, distributed messaging, disaster recovery, web administration, production deployment orchestration, and advanced plugin/agent isolation are deferred until their prerequisites are proven.

## Human gates
External financial actions, contracts, credentials, irreversible destructive operations, and other authority-bearing side effects remain permission-gated.
