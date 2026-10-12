# Brain Foundation Toolkit

This first implementation consolidates reusable tools for the recurring blockers found
in the Brain Cloud / Windows Server 2025 path.

## Components

| Component | Purpose | Safety boundary |
|---|---|---|
| `brain_v12/tools/blocker_to_action.py` | Maps known blocker codes to one actionable next step and deduplicates repeats | No execution or mutation |
| `brain_v12/tools/cloud_secret_readiness.py` | Reports required environment-variable presence | Never prints values; presence is not validity |
| `brain_v12/tools/runner_capability_preflight.py` | Checks Linux x64, KVM, utilities, registry configuration and contract path | No cloud calls or resource creation; never proves boot |
| `brain_v12/tools/golden_checkpoint_verify.py` | Verifies checkpoint file hashes against a manifest | Read-only; does not restore files |
| `brain_v12/self_healing/tool_evolution.py` | Records each BrainAI tool invocation and maintains improvement proposals | Redacted telemetry; no automatic source rewrite |

## Universal invocation policy

`BrainAI.execute_tool` records every tool attempt, including unknown tools, denials,
handler failures, invalid return types, and successful results. It records only parameter
shape, not parameter values or returned data. Other tool entry points should use
`invoke_observed(tool_name, handler, params, risk=..., permission=...)`.

Each invocation refreshes per-tool improvement proposals based on failure repetition,
latency, and governance denials. The same failure is not a reason to repeat the same
action indefinitely.

## Evolution lifecycle

1. Observe invocation and sanitized outcome.
2. Update the per-tool history and improvement proposal.
3. Convert repeated or high-priority proposals into a regression test and patch proposal.
4. Run targeted tests, full relevant CI, and independent verification.
5. Merge/register only through the normal reviewed release gate.

**Important:** "Improve on every invocation" means every call contributes evidence and
updates the next improvement proposal. It does not mean arbitrary code is rewritten or
executed during the call. Automatic self-modification would undermine permissions,
reproducibility, and evidence integrity. Any source change remains review- and test-gated.

## Known limits / follow-up

- Presence checks do not prove a secret is valid or that GitHub permissions allow its use.
- The runner preflight does not execute a probe and does not prove a trusted runner is online.
- The checkpoint verifier checks hashes only; it does not perform a restore drill.
- The blocker catalog should be extended only with stable codes supported by logs/tests.
- Secret creation/update still requires an authorized GitHub secret-write integration and
  explicit operator authority; no secret value is accepted by these tools.
