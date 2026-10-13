# Brain Revenue Autopilot — Execution Plan

**Status:** Proposed; implementation and revenue are not yet verified.  
**Repository:** `omarenserat1980/MySimpleProject`  
**Operating principle:** Free-first, software-only by default, evidence-gated, and no unapproved spending or financial side effects.

## Objective

Turn existing Brain opportunity, task, media, and revenue capabilities into one auditable path from opportunity discovery to verified payment. Reuse existing modules and the single orchestrator; do not create competing supervisors, duplicate ledgers, or unbounded self-healing workflows.

## Known baseline and constraints

- The repository README describes Brain Cloud as software-only and the mining economics layer as analytical only.
- A task, opportunity, generated asset, published post, invoice, or expected payout is **not** realized revenue.
- Record realized revenue only when unique, independently verifiable payment evidence is matched to the beneficiary, amount, currency, and transaction/payment reference.
- Do not store credentials, private keys, payment tokens, or sensitive customer data in source, logs, reports, or artifacts.
- No purchases, paid ads, subscriptions, contracts, withdrawals, transfers, wallet operations, cloud provisioning, or external submissions without the applicable explicit authorization.
- Do not treat simulator success, a green CI run, or a worker heartbeat as proof of a real customer delivery or payment.

## Revenue lifecycle

`OBSERVE → DISCOVER → SCORE → SELECT → AUTHORIZE → EXECUTE → VERIFY_DELIVERY → MATCH_PAYMENT → RECORD_REVENUE → LEARN`

Every transition must be durable, idempotent, and auditable. A failed gate must stop the consequential action and emit a sanitized reason code plus the next safe action.

## Initial revenue strategy

1. **Digital services first:** prepare service packages for video editing, original short-form content, thumbnails, metadata, and content repurposing. Prepare proposals and drafts automatically; require human approval before sending proposals, accepting contractual terms, or making commitments.
2. **Original media workflow second:** produce a small number of quality-checked, rights-aware sample assets. Require technical QC and a separate content/originality/rights review before publication. Treat platform monetization as unavailable until the account's eligibility and actual payouts are verified.
3. **Mining economics only as a read-only analysis:** use current, sourced inputs when available; show assumptions, uncertainty, electricity and fees. Never infer mining income from simulation, and do not launch miners, buy hardware, or connect wallets under this plan.

## MVP implementation sequence

### Phase 0 — Audit before edits
- Locate and inspect existing opportunity lifecycle, revenue ledger/evidence store, permissions/authority gate, task queue, media QC, and relevant tests.
- Map existing APIs and workflows; identify the single canonical path and reuse it.
- Record baseline commit, current open PRs, CI state, and any duplicated or conflicting implementation.
- Do not merge or deploy unrelated open PRs as a shortcut.

### Phase 1 — Revenue contracts and state model
Use the existing canonical storage where possible. Ensure each opportunity/payment has stable IDs and idempotency keys. Keep these states distinct:
- `DISCOVERED`, `QUALIFIED`, `PROPOSAL_DRAFTED`, `AWAITING_HUMAN_APPROVAL`
- `AUTHORIZED`, `IN_PROGRESS`, `DELIVERED_PENDING_VERIFICATION`
- `PAYMENT_EXPECTED`, `PAYMENT_RECEIVED_UNVERIFIED`, `REVENUE_REALIZED`
- `REJECTED`, `BLOCKED`, `FAILED`, `REFUNDED`

Do not create a second source of truth if the existing ledger can represent these states. Revenue views should be replayable from evidence and idempotent.

### Phase 2 — Permission and evidence gates
- Discovery, scoring, local generation, QC, and proposal drafting may run autonomously within configured resource limits.
- External publication, client contact/submission, contract acceptance, purchases, paid advertising, and all movement of money remain approval-gated.
- Reject legacy approval booleans as sufficient authority for consequential execution; use the repository's current authority/contract mechanism.
- Require evidence metadata, integrity checks, unique payment reference, amount/currency, timestamp, and independent verification status before marking revenue realized.
- Redact secrets and sensitive information from logs.

### Phase 3 — One durable worker
- Reuse the existing canonical worker and persistent queue.
- Enforce bounded retries, exponential backoff, idempotency, lease/fencing where supported, restart recovery, dead-letter state, and heartbeat freshness.
- A heartbeat proves liveness only; task completion requires result evidence and a verification gate.
- Do not add a new cloud service or paid infrastructure. Keep software-only tests available.

### Phase 4 — First customer-ready offer
- Generate one clearly scoped service package with sample deliverables, turnaround, revision limits, and a truthful price proposal.
- Run local production and QC on a sample; generate a delivery manifest and checklist.
- Draft outreach and proposals, but wait for explicit human approval before sending.
- Track inquiries, accepted work, delivery, payment status, fees, refunds, and net realized income.

### Phase 5 — Review and scale
- Report weekly: qualified opportunities, approved submissions, paid customers, verified gross receipts, fees, refunds, net realized revenue, delivery time, failure rate, and unresolved blockers.
- Compare channels using realized net revenue and labor/resource cost, not views, clicks, or predicted payouts.
- Expand only after repeatable evidence of positive net economics.

## Required tests

- Opportunity/task retries cannot create duplicate work or duplicate revenue entries.
- Missing, malformed, duplicate, mismatched, or unverified payment evidence never yields `REVENUE_REALIZED`.
- Expected/receivable/unverified/paid/refunded states remain distinct.
- External side effects fail closed without the required authority and execution contract.
- Logs and artifacts do not contain credentials or payment secrets.
- Worker restart restores pending work; retry limits and dead-letter handling prevent infinite loops.
- Simulator results are labeled simulated and cannot satisfy real-delivery or real-payment gates.
- Media release requires both technical QC and the appropriate content/rights review.
- Run focused tests, then the relevant full CI workflow; attach evidence and report failures without masking them.

## Acceptance criteria

The MVP is accepted only when:
1. A real, authorized service workflow can be executed end-to-end in a supported environment.
2. Delivery is independently verified.
3. A real payment can be matched to trustworthy evidence and recorded exactly once.
4. The ledger calculates gross receipts, fees, refunds, and net realized revenue correctly.
5. The system survives restart and safely resumes without duplicate side effects.
6. All authorization, quality, and evidence tests pass in CI.
7. A sanitized report distinguishes implemented, tested, deployed, and revenue-realized states.

## Explicit non-goals for this MVP

- No guarantee of income or a target amount of revenue.
- No automatic spending, paid advertising, contract acceptance, financial transfers, wallet access, or mining execution.
- No claim that Windows Server 2025 or any real cloud VM is running based on preflight or simulation.
- No production/deployment claim until the approved release path and live health/evidence checks succeed.

## First implementation task

Complete Phase 0 and report the exact existing files, canonical APIs, current tests, gaps, and the smallest test-first code change. Implement only after this map is grounded in the current repository state.
