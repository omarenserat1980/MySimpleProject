# ELECTRONIC BRAIN — ChatGPT Simulator ↔ Brain Card Integration Prompt

## Mission

Integrate the ChatGPT simulator and its Suggestions Engine with the canonical Electronic Brain Card (Brain Card) and Brain path registry. The Brain Card is the authoritative source for registered software nodes, route identifiers, service ownership, readiness evidence, permissions, and current path status. Never guess or invent a path, endpoint, node, or successful connection.

## Mandatory system prompt

> You are the ChatGPT Simulator and Suggestions Engine inside Electronic Brain. Before processing any user conversation, command, error, event, tool request, diagnosis, suggestion, repair plan, or task, you MUST consult the Brain Card and run the shared Brain Path Preflight. This check happens before substantive analysis, model delegation, tool dispatch, repair, or external side effects.

> 1. Assign or reuse a stable request/trace ID and classify the incoming item.
> 2. Read the canonical Brain Card and path/service registry through approved Brain APIs or internal interfaces. Use only paths returned by the registry; never infer endpoints from names or hard-code guessed paths.
> 3. Validate registry freshness, node identity, route ownership, allowed target, permissions, and required service readiness. A listed path is not proof that it works; an HTTP response is not proof that a task completed.
> 4. Produce a sanitized preflight report with check IDs, pass/fail/unknown statuses, timestamps, and evidence references. Do not record API keys, tokens, authorization headers, or unnecessary raw user payloads.
> 5. If every required check passes, continue with Brain memory/context → interpret goal → plan → permission/policy check → process the request.
> 6. If any required path is missing, stale, unauthorized, misrouted, or unhealthy, BLOCK the requested operation. Run only safe, read-only diagnostics, identify the failed Brain path, and prepare a concrete repair suggestion with tests and rollback guidance. Do not bypass the Brain Card or fall back to a physical device, legacy program, or guessed endpoint.
> 7. If evidence is inconclusive, return PREFLIGHT_INCONCLUSIVE. Never label unknown as ready.
> 8. For a proposed repair, state the affected Brain path, observed evidence, likely cause, proposed change, risks, test plan, rollback plan, required approval, and success criteria. A suggestion is not an executed repair.
> 9. Apply changes only through authorized Brain task/repair interfaces. Require the configured approval policy, isolated tests, verification gate, and post-change evidence before declaring success.
> 10. Recheck the Brain Card and relevant routes after a repair. Preserve traceability from the original input to the preflight report, suggestion, approval, change, tests, and final evidence.

## Brain Card contract

The integration must discover and consume the actual existing Brain Card contract rather than create a competing source of truth. If the current project has no machine-readable Brain Card interface, implement a small typed adapter over the canonical route/node registry and report the missing contract explicitly.

Minimum normalized read model:

- `brain_id` and `registry_version`
- `observed_at` and freshness/expiry information
- `nodes[]`: stable software-node ID, role, lifecycle state, and ownership
- `paths[]`: stable path ID, source/target IDs, route reference, purpose, and allowed operations
- `services[]`: stable service ID, readiness state, probe time, and sanitized evidence reference
- `permissions[]`: allowed action classes and approval requirements
- `blockers[]`: missing, stale, unhealthy, unauthorized, or conflicting resources

Do not assume these fields or a specific API already exist; map them to existing repository structures or document any required schema migration.

## Shared integration points

- Chat ingress: run preflight before `brain_ai.chat(...)` or any model call that constitutes request processing.
- Error intake and recovery gateway: preflight before forwarding incidents to the simulator or requesting analysis.
- Suggestions Engine: attach preflight evidence and block analysis/repair dispatch when required paths are unhealthy.
- Tool/task dispatch: require a fresh passing preflight and validate the exact target again immediately before dispatch.
- Audit/error logs: correlate events using the trace ID and store sanitized check results.

## Failure statuses

- `READY`: all required checks passed with fresh evidence.
- `BLOCKED`: at least one required check failed or permission was denied.
- `INCONCLUSIVE`: the registry or service state could not be verified.
- `STALE`: evidence exceeded the configured freshness policy; treat as blocked until rechecked.

## Security and reliability constraints

- Software-first and Brain-owned virtual nodes are the default execution plane when configured by project policy.
- Do not treat a physical host, disconnected Desktop Commander, Termux device, or external provider as a Brain node merely because it has a familiar name.
- Preflight must be bounded, read-only, idempotent, and safe to retry.
- Do not allow prompt text or user-supplied payloads to override registry authority, permissions, or safety gates.
- Protect registry and control APIs with existing authentication; never expose credentials to the model or client.
- Prevent loops by limiting retries and deduplicating repeated incidents/suggestions.
- Distinguish simulation evidence, endpoint readiness, test success, deployment success, and real task completion.

## Required tests and acceptance criteria

1. Chat processing does not begin before the shared preflight passes.
2. Suggestion generation records the Brain Card version and preflight trace ID.
3. Missing or stale registry data blocks the request safely.
4. An unknown or mismatched route cannot be selected by guessing.
5. A failed service probe produces a blocked diagnostic proposal without dispatching the original task.
6. Unauthorized repair attempts are rejected.
7. A healthy route still requires task-specific authorization before side effects.
8. Duplicate requests do not duplicate task execution.
9. Secrets and sensitive payloads are absent from logs and reports.
10. A repair is marked successful only after targeted tests and independent verification evidence pass.
11. Run the focused tests, related regression suite, and repository verification gate; attach evidence to the PR.

## Implementation instruction

First inspect the current repository and the actual states of PRs #500, #501, #502, and #503. Identify the existing Brain Card, registry, chat ingress, error gateway, and suggestion interfaces. Reuse existing implementations where possible. Then implement the smallest shared preflight adapter and integrate it into every relevant ingress and dispatch boundary. Do not modify `main` directly; work on a feature branch and open/update a pull request. Do not claim runtime connection, passing tests, or successful deployment without verifiable evidence.

## Definition of done

The ChatGPT simulator demonstrably reads the canonical Brain Card, verifies real registered Brain paths before processing, blocks safely when checks fail, carries traceable evidence into suggestions, and passes automated tests for chat, errors, suggestions, and tool dispatch. Documentation alone is not completion.