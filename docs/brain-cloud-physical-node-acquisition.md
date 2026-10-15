# Brain Cloud-Assisted Physical Node Acquisition

## Goal

Use Brain cloud orchestration to discover and prepare an owner-authorized, genuinely physical execution host while preserving the zero-budget requirement. Cloud orchestration is not itself a physical worker and must never be represented as one.

## Brain-owned control plane and tool routing

Brain is the orchestrator, not a cloud-compute provider by itself. Its connected tools must be the first discovery surface: enumerate available computer/device connectors, repository/CI execution, and explicitly connected cloud-provider APIs; record each tool's actual capabilities and authorization state; and route only to tools that can perform the requested operation. Never infer that a tool can provision compute merely because it can edit GitHub or run CI. If no persistent executor or authorized provider adapter is connected, return `NO_AUTHORIZED_PROVIDER` with the missing connector/capability names instead of looping on user prompts or fabricating credentials. GitHub Actions may run bounded discovery and tests, but is not a substitute for a persistent host.

## Architecture

1. Cloud discovery coordinator: enumerate only provider accounts/connectors explicitly authorized by the owner. Report connector availability and provider API failures distinctly.
2. Offer verifier: require current authoritative price, region, hardware/CPU limits, storage/network limits, duration, quotas, expiry, payment-method requirements, and cleanup route. A free trial, credits, promotional quota, or free tier requiring a payment method is not automatically accepted as zero-cost.
3. Resource decision gate: accept only verified zero-cost offers with no card, deposit, activation fee, or hidden usage fee. If pricing is uncertain, fail closed.
4. Owner approval: before provisioning, display exact provider, resource size, region, duration/expiry, data access, cost limits, and cleanup operation. Do not create external resources before approval.
5. Provisioner adapter: after approval, use only documented provider APIs with credentials held in a runtime secret store. Grant least privilege. Never place credentials in source, logs, workflow artifacts, issue comments, or chat.
6. Bootstrap: install/configure the minimal Brain agent using signed or version-pinned artifacts. Do not install a miner, wallet, pool credentials, or unrelated software automatically.
7. Identity and connectivity proof: collect provider instance ID, instance metadata/attestation where available, agent version, boot ID, fresh nonce, timestamp, and authenticated HTTPS heartbeat. Distinguish provider-backed facts from agent self-reports.
8. Durable registry and audit: persist node lifecycle and evidence outside process memory, reject replayed/stale evidence, and record provision, rotate, revoke, and terminate actions.
9. Cost/expiry watchdog: periodically re-check quotas and expiry. If cost becomes non-zero or unclear, stop new tasks and request owner action. Terminate only resources whose ownership and cleanup action are confirmed and authorized.
10. Mining evidence (separate scope): worker telemetry alone never proves mining. If separately authorized, verify accepted shares with the pool's official interface and payouts independently.

## GitHub Actions boundary

GitHub-hosted Actions can lint, test, build, and run short-lived orchestration jobs. They are ephemeral CI runners, not persistent physical mining nodes. Do not keep a job alive to evade service limits or claim that a passing workflow proves a persistent host. Use workflows only for bounded checks and evidence packaging, with no secrets printed.

## Required node states

- DISCOVERY_UNAVAILABLE
- NO_AUTHORIZED_PROVIDER
- CANDIDATE_UNVERIFIED
- BLOCKED_COST_UNCERTAIN
- AWAITING_OWNER_APPROVAL
- PROVISIONING_APPROVED
- BOOTSTRAP_FAILED
- CONNECTED_UNVERIFIED
- PHYSICAL_NODE_VERIFIED
- QUARANTINED
- TERMINATION_REQUIRED

Each transition records UTC time, source, actor, evidence references, and reason. Simulated nodes, CI runners, provider marketing pages, and self-reported telemetry cannot satisfy PHYSICAL_NODE_VERIFIED.

## Failure behavior

- No connected device or provider credential: record NO_AUTHORIZED_PROVIDER; do not invent access. Brain must report the actual connected-tool inventory and missing capability rather than asking the owner to repeat details already in the project context.
- No confirmed zero-cost offer: record BLOCKED_COST_UNCERTAIN; do not provision.
- Owner approval absent: no external side effect.
- Provider API unavailable: retry with bounded exponential backoff, then stop and report the blocker.
- Identity, freshness, or authentication failure: quarantine and revoke the node credential where authorized.
- No pool-side accepted-share evidence: mining outcome remains unverified.

## Current known limitations

The available device connector previously returned No computers found for this user. No provider connection or deployable zero-cost physical host has been demonstrated. This document defines the implementation contract; it does not provision a cloud account, create an instance, or prove physical execution. Durable evidence storage and provider-specific adapters must be implemented and tested before claiming autonomous provisioning.
