# Electronic Brain — Project Master Specification

## 1. Purpose
Electronic Brain is an evidence-first automation and business platform whose source of truth is this GitHub repository. It is designed to inspect, plan, execute, verify, repair, retry, document work, and turn validated capabilities into lawful, evidence-backed economic outcomes.

## 2. New top-level success principle: economic outcome
Engineering health and commercial success are separate states.

- A green test, workflow, feature, API, page, model, or plan proves engineering progress only.
- A monetizable capability is commercially successful only when a real customer/buyer or other legitimate revenue source is evidenced and payment is independently verified.
- Profit is a stronger state than revenue and requires verified revenue plus verified attributable costs.
- Forecasts, market size, hashprice, traffic, leads, clicks, opportunities, invoices, or expected revenue are not realized revenue.
- The Brain must continuously expose the gap between technical completion and monetary realization.

Commercial state progression:
MONETIZATION_PATH_DEFINED -> CUSTOMER_VALIDATED -> PAYMENT_VERIFIED -> REVENUE_REALIZED -> PROFIT_VERIFIED

The state is evidence-driven and must never be advanced by a green CI run alone.

## 3. Core principles
- GitHub repository and committed code are the source of truth.
- Never treat file existence, a green planning step, or a queued run as proof of completion.
- Every autonomous action must have bounded scope, observable evidence, and a verifiable result.
- External side effects such as publishing, payments, withdrawals, or applications require explicit authorization.
- Free/open-source infrastructure is preferred; the current cloud control plane is GitHub-hosted Actions.
- Recovery must be idempotent where possible and must not create infinite retry loops.
- No automatic purchase, contract, withdrawal, or movement of funds.
- Revenue recognition requires auditable evidence; economics forecasts remain analysis.

## 4. Major subsystems
- Brain Core / orchestration
- Memory and audit state
- Decision and task engines
- Supervisor and self-healing
- Causal/runtime diagnostics
- Media Engine and Cinematic Factory
- Quran knowledge/reasoning layer
- Device Bridge / BRAIN Termux Emulator
- GitHub Cloud runner
- Economic Ledger and opportunity workflows
- Commercial Outcome Gate
- Customer, sales, offer, delivery, and revenue evidence workflows
- Verification, security, health, and recovery

## 5. Business loop
Every monetizable Brain capability should have a measurable loop:
Discover demand -> Define offer -> Build -> Validate -> Acquire customer -> Deliver -> Verify payment -> Record revenue -> Verify costs -> Measure profit -> Improve

The Brain should prioritize work that closes this loop, while keeping customer acquisition, contracts, payments, and withdrawals permission-gated.

## 6. Task lifecycle
PENDING -> RUNNING -> SUCCESS | FAILED | CANCELLED | RETRYING

A task may only enter a terminal success state after its declared verification contract passes. For commercial tasks, engineering success and commercial outcome are recorded separately.

## 7. Autonomous recovery contract
The Supervisor follows:
discover -> plan -> select_backend -> execute -> verify -> repair -> retry -> deliver

Recovery is bounded by attempt/cycle limits and uses classified failures rather than blind reruns.

## 8. Cinematic verification
A movie is not considered production-complete because a workflow succeeds. The intended evidence chain is:
Render -> QC -> FFmpeg -> Master QC -> final.mp4 -> VERIFIED_COMPLETED

A separate commercial chain is required for monetary success:
offer -> customer -> payment verification -> delivery evidence -> revenue -> attributable costs -> profit.

## 9. Cloud execution
GitHub Actions provides ephemeral Linux runners. They are not persistent virtual machines. Persistent state must therefore be stored in repository artifacts/state or another explicitly configured durable layer.

## 10. Economic and financial safety
- The Economic Ledger is an evidence system, not a bank or payment executor.
- The Brain may research opportunities, model unit economics, prepare offers, measure outcomes, and reconcile supplied evidence.
- It must not infer revenue from projections.
- It must not move funds or withdraw money automatically.
- Financial success requires independently auditable evidence.

## 11. Change discipline
Changes should follow:
inspect -> backup/evidence -> smallest safe change -> tests -> verify -> commit -> rerun -> inspect result.

## 12. Security
Tokens and secrets must never be committed. Autonomous workflows must use least-privilege permissions and must not infer financial success from an unverified ledger entry.

## 13. Current implementation status
The repository contains the major Brain V12 modules and economic workflows. Runtime audits remain authoritative for what is actually working.
