# Brain Preflight Gate — Required Before Any Processing

## Goal

Every input received by the Electronic Brain ChatGPT simulator—conversation text, command, reported fault, tool request, event, or repair request—must pass through a Brain Path Preflight before any substantive analysis, model call, tool call, diagnosis, or execution.

This is a control-plane requirement, not a claim that a live simulator is already connected.

## Mandatory order

1. **Receive and classify only**: assign a trace/request ID and classify the input type. Do not execute the requested operation yet.
2. **Resolve canonical Brain paths**: load the configured runtime roots and registered Brain API/service routes from the repository's canonical registry. Do not guess routes from names.
3. **Check path integrity**: validate that each required path/route exists, is permitted, resolves to the expected Brain-owned target, and is not stale or shadowed by a legacy/hardware route.
4. **Probe readiness**: perform bounded, read-only health checks for required internal services. Separate route existence from service readiness and actual task completion.
5. **Build a preflight report**: record trace ID, input class, paths checked, pass/fail/unknown per check, timestamps, and safe evidence references. Never log secrets, authorization headers, or raw sensitive request bodies.
6. **Gate the operation**:
   - If required paths and services are healthy, continue to Brain context/memory → plan → policy/permission checks → processing.
   - If a required path is missing, invalid, or unhealthy, stop the requested operation and run only safe diagnostics. Produce a repair proposal; do not silently bypass the gate.
   - If the check is inconclusive, return PREFLIGHT_INCONCLUSIVE and request/retry diagnostics within a bounded budget.
7. **Verify after action**: for any approved repair, run targeted tests and the Brain verification gate; record before/after evidence and rollback guidance.

## Integration points

The gate must be shared rather than reimplemented separately:

- Browser/API chat ingress (brain_v12/brain/chat_session_api.py) before brain_ai.chat(...).
- Unified error intake (POST /api/errors/report, PR #500) before forwarding an incident to the simulator.
- Durable error logging/traceability (PR #501): attach the preflight trace ID and check results to the incident record.
- Suggestions & Intelligent Repair Engine (PR #502): require a successful or explicitly waived preflight before analysis; an unhealthy path becomes a diagnosis target, not a reason to bypass the gate.
- Tool/task dispatch, simulator commands, and future event/webhook ingress: use the same gate contract.

## Result contract

A preflight result should expose:

- ok: true only when every required check passes
- status: READY, BLOCKED, or INCONCLUSIVE
- trace_id
- input_kind
- checks[]: stable check ID, target ID, status, elapsed time, and sanitized evidence reference
- blocked_reasons[]
- checked_at (UTC)

Do not include secret values, tokens, raw authorization headers, or full user payloads in the report.

## Safety and routing rules

- Software-first Brain nodes and Brain-owned virtual routes are canonical; physical devices, stale desktop connections, Termux hardware agents, and external tools must not be treated as the default execution target.
- A successful HTTP response or registered route proves only that the endpoint responded; it does not prove the requested task completed.
- No shell/code execution, repair patch, deployment, publishing, or external side effect may occur during preflight.
- Repairs remain proposal-first and must pass authorization, isolated testing, verification, and evidence gates.
- Fail closed for unknown routes, missing credentials, failed required checks, and untrusted redirect targets.
- Use bounded timeouts, deduplication, and a small retry budget to avoid loops.

## Acceptance tests

1. A normal chat message cannot call the model until preflight passes.
2. A command cannot dispatch to a tool before preflight passes.
3. An error cannot be forwarded to the simulator before preflight passes.
4. A missing route blocks processing and creates a sanitized diagnostic report.
5. A stale/legacy hardware target is rejected when software-only routing is configured.
6. An inconclusive health probe does not count as success.
7. Duplicate retries retain the same trace/request identity and do not duplicate side effects.
8. Secrets and sensitive payloads are absent from logs and preflight output.
9. Every successful repair proposal is followed by targeted tests and independent verification evidence.
10. CI tests cover the gate and all ingress integrations.

## Dependency and current status

This design is intended to integrate with PR #500 (unified error recovery gateway), PR #501 (durable error logs), and PR #502 (suggestions/repair engine). Those integrations must be checked against their actual merged state before implementation.

**Status: specification added; runtime enforcement, end-to-end ChatGPT connectivity, and live path health are not yet verified.**

## Implementation status (2026-10-12)

The first executable gate is now wired into the browser chat session endpoint and the direct Brain AI chat/tool endpoints. It checks the route registered in the live in-process FastAPI router, the AI/store callable interfaces required by that ingress, and the configured software execution plane. It returns a sanitized report and blocks before message persistence, model processing, or direct tool dispatch when a required check fails. Trace IDs and the Brain Card contract version are attached to responses/metadata.

Important limitation: repository search did not identify an existing machine-readable canonical Brain Card registry. The current adapter therefore exposes an explicitly versioned in-process route/service snapshot; it does **not** verify external deployment health, a remote simulator, PR #500/#501/#502 error/suggestion paths, or every future task/event ingress. Those integrations and passing targeted CI remain required before this contract can be called complete.
