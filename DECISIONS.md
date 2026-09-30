# Electronic Brain — Decisions

## 2026-09-30 — Provider-neutral runtime
Decision: Brain must not depend on Render, Oracle Cloud, or Google Cloud.
Reason: preserve portability, free/open-source operation, and user control.

## 2026-09-30 — Evidence-first completion
Decision: workflow success is insufficient. Product success requires task-specific evidence.
Reason: prevent false positives.

## 2026-09-30 — Worker lease model
Decision: every executable job must have an exclusive, renewable lease with bounded attempts.
Reason: prevent duplicate execution and uncontrolled retry loops.

## 2026-09-30 — Fail-closed external actions
Decision: money, publishing, contracts, external submission, signing, and policy changes require explicit authorization.
Reason: protect user agency and assets.

## 2026-09-30 — BRAIN-native device adapter
Decision: the local device bridge is a Brain worker adapter, not a dependency on an external Termux service.
Reason: keep the execution contract inside Brain while allowing user-owned hardware to contribute compute.

## 2026-09-30 — Free-first media
Decision: local/open-source media processing is the default. Paid generation APIs are optional adapters, never mandatory.
Reason: preserve the user's no-payment requirement.
