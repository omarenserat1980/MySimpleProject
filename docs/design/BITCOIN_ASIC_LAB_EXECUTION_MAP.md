# Bitcoin ASIC Lab — Universal Design Factory Execution Map

Date: 2026-10-14
Repository: `omarenserat1980/MySimpleProject`

## Purpose
Connect the Universal Design Factory's specialist prompts and evidence rules to the existing Bitcoin ASIC work without duplicating modules or collapsing distinct proof levels.

## Current tracked work

| Stage | Existing PR | Scope | Required interpretation |
|---|---:|---|---|
| SHA-256 compression RTL | #647 | One compression block and known vector | RTL reference milestone |
| Fixed-length SHA256d | #648 | Two compression blocks for a 32-byte message | Not the full Bitcoin header |
| 80-byte header SHA256d | #649 | Bitcoin header serialization and known vector | Header hash computation only |
| Target comparison | #650 | Digest byte order and target comparator | Comparison primitive only |
| Stratum protocol probe | #651 | Bounded, disabled-by-default protocol probe | Connection/authorization checks only |
| Bounded nonce search | #652 | Clocked bounded nonce-search controller | RTL reference, not optimized silicon |
| Generic synthesis preflight | #655 | Yosys readiness and evidence bundle | Generic synthesis only |
| PDK/platform readiness | #656 | Pinned OpenROAD-flow platform audit | Tool/platform readiness only |
| Physical-flow experiment | #657 | Experimental OpenROAD flow and reports | Not signoff or fabrication |
| Live mining evidence gate | #640 | Fail-closed evidence validator | Validation logic only; no live mining |
| Bitcoin North Star | #644 | Cross-system mining goal and evidence direction | Review dependency and integration before merge |
| Universal Design Factory | #658 | Specialist prompts, routing, evidence classification | Orchestration policy and test coverage only |

PR status and dependencies must be checked live before any merge. Do not assume the numerical order alone is a valid merge order; use each PR's actual base/head and dependency chain.

## Required execution order

1. **Discovery and branch hygiene** — Prompt 01: inspect each PR's base/head, CI, changed files, and dependencies. Avoid merging stacked PRs directly into `main` out of order.
2. **RTL reference verification** — Prompts 06 and 10: require independent known-answer vectors and passing RTL simulation for each primitive; preserve byte-order and nonce-boundary tests.
3. **Nonce-search integration** — verify the controller against the header hash and target comparator, including bounded search exhaustion and reset behavior.
4. **Generic synthesis** — capture the netlist, tool versions, logs, manifest, and checksums. Do not equate generic synthesis with physical design.
5. **PDK and physical flow** — confirm the pinned platform actually exists, then run available place/route and physical checks. Treat experimental constraints and GDS as candidates until independent review and required signoff.
6. **Pool protocol** — Prompt 09/10: keep live network access disabled by default; test malformed, stale, unauthorized, and failed TLS/Stratum cases offline.
7. **Live-mining proof** — use the validator in PR #640 only against fresh, attributable evidence from an actually authorized worker: live mode, worker identity, pool connection and authorization, measured positive hashrate, and accepted shares. CI fixtures must never pass as live evidence.
8. **Revenue proof** — keep separate from mining activity. Require independently reconcilable provider/payment and realized-revenue evidence; no test fixture or accepted share alone proves revenue.
9. **Release review** — Prompt 14: publish a per-gate matrix and unresolved blockers. No automatic merge, deployment, spend, secret mutation, or fabrication.

## Evidence vocabulary

- `TESTED`: a specified test ran and its result is captured.
- `SIMULATED`: a named simulation ran; never physical proof.
- `VERIFIED`: the specific claim has supporting evidence and independent review.
- `BLOCKED`: a required tool, permission, physical worker, or evidence source is absent.
- `HARDWARE_VERIFIED`: direct physical-device evidence exists.
- `MANUFACTURED_VERIFIED`: manufacturing evidence exists.
- `REVENUE_VERIFIED`: reconciled financial/provider evidence exists.

Never promote a status solely because a workflow is green.

## Current hard constraints
- Zero budget and free/open-source-first.
- No phone or remote device is assumed available.
- Simulation remains distinct from physical hardware.
- A GitHub-hosted CI runner is ephemeral and is not a persistent mining worker.
- No ASIC fabrication, physical mining, accepted shares, or realized revenue is claimed by this roadmap.
