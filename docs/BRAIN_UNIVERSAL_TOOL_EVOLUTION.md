# Brain Universal Tool Evolution

Every invocation routed through `BrainAI.execute_tool` is observed by the shared
self-improvement layer. The same `invoke_observed` adapter is available for tools
implemented outside BrainAI.

## Behavior

- Appends redacted invocation metadata to `.brain/state/tool_evolution/invocations.jsonl`.
- Maintains per-tool proposals in `improvement_proposals.json`.
- Records parameter shape only, never parameter values or tool output.
- Detects repeated identical failure signatures and proposes stopping retry loops.
- Tracks slow calls and permission/approval denials as improvement opportunities.
- Telemetry failure never turns a failed tool into a successful tool.

## Safety contract

This layer does **not** rewrite Python files or execute generated code during a tool
call. It produces evidence-backed proposals. Source changes require a separate reviewed
patch, tests, and the existing verification/release gates. High-risk tools remain behind
their current approval and permission checks. It never escalates privileges or changes
secrets automatically.

## State location

Uses `BRAIN_RUNTIME_HOME/.brain/state/tool_evolution` when configured; otherwise
uses the repository's `.brain/state/tool_evolution`. Protect this directory as runtime
state and do not commit real invocation data.
