# Brain Zero-Budget Physical Node Acquisition Contract

## Objective

Brain should autonomously discover and prepare a genuine physical execution node using only an already-authorized host or a resource that is verifiably free. This is an acquisition and readiness workflow, not a simulator. A software registry entry, virtual profile, CI runner, advertised free trial, provider credit, or claimed hashrate must never be relabeled as a persistent physical mining worker.

## Hard constraints

- Total upfront and recurring cost must be zero: no card, deposit, activation, subscription, upgrade, withdrawal, or hidden usage fee.
- Use only hosts/accounts the owner has explicitly authorized. Do not scan public IP ranges, install agents on third-party machines, bypass provider controls, or use credentials outside their intended scope.
- Do not create cloud resources, accept terms, enter payment details, or activate a trial automatically. Require explicit owner approval before any external provider activation.
- Never commit credentials. Use the host's secret store/environment; never ask the owner to paste tokens into chat.
- Never claim a physical node exists until provider/host identity and direct live evidence are recorded.
- Never claim mining success from worker self-reports alone. Pool-accepted shares and payout require independent evidence.

## Brain execution sequence

1. **DISCOVER_AUTHORIZED_RESOURCES** — enumerate only explicitly connected device agents and owner-authorized provider connectors. Record the source and time of each observation. If none are connected, return `NO_AUTHORIZED_PHYSICAL_RESOURCE` and stop provisioning.
2. **VERIFY_RESOURCE_AND_ZERO_COST** — establish physical host/device identity and the exact price/limits from an authoritative provider source. Reject simulation-only nodes, ephemeral CI workers for persistent service, unverified offers, and any offer requiring payment details or later payment.
3. **APPROVAL_GATE** — present provider, hardware model, duration, geographic region, full price/usage limits, data access, and termination method. Do not activate or provision until the owner explicitly approves that specific resource.
4. **PROVISION_MINIMAL_AGENT** — after approval, use only the provider's documented API or a host agent already installed by the owner. Install a least-privilege telemetry agent; do not install a miner, wallet, or pool configuration as part of node provisioning.
5. **AUTHENTICATE** — generate a cryptographically random token on the authorized host, transfer it directly to the Brain runtime secret store through an approved secret mechanism, enforce HTTPS, rotate/revoke credentials, and never log secrets.
6. **PROVE_PHYSICAL_CONNECTION** — capture host/provider identity, agent version, boot ID, task/nonce, UTC observation time, authenticated heartbeat, last-contact time, and signed or provider-backed attestation where available. Keep self-reported fields clearly marked as self-reported.
7. **ACCEPT_OR_QUARANTINE** — mark a node `PHYSICAL_CONNECTED_UNVERIFIED` after authenticated heartbeat only. Mark it `PHYSICAL_VERIFIED` only when host identity and freshness evidence meet policy. Quarantine stale, replayed, mismatched, or unverifiable evidence.
8. **OPTIONAL_MINING_EVIDENCE** — only if the owner separately authorizes mining and a legitimate miner is already configured, collect miner telemetry. Verify accepted shares independently through the pool's official dashboard/API; verify payout separately. Do not handle wallet funds.
9. **AUDIT_AND_SHUTDOWN** — persist append-only evidence and configuration changes, monitor cost/expiry, and provide a revocation and teardown path.

## Required states

- `NO_AUTHORIZED_PHYSICAL_RESOURCE`
- `CANDIDATE_UNVERIFIED`
- `AWAITING_OWNER_APPROVAL`
- `PROVISIONING_APPROVED_RESOURCE`
- `PHYSICAL_CONNECTED_UNVERIFIED`
- `PHYSICAL_VERIFIED`
- `QUARANTINED`
- `BLOCKED_COST_OR_AUTHORIZATION`

Every transition must include a timestamp, reason, evidence references, and actor. Never transition to a verified state based only on a simulated workload, successful CI, API reachability, or self-reported hashrate.

## Current known blocker

A previous device connector query returned `No computers found for this user`. Therefore no physical host can be provisioned through that connector at present. This contract cannot create hardware from software and must not invent a device or claim a live connection. Brain can continue discovery and prepare configuration, but provisioning must remain blocked until an authorized real host or verifiably zero-cost resource is available.

## Acceptance tests

- No connected/authorized host -> `NO_AUTHORIZED_PHYSICAL_RESOURCE`; no provisioning call.
- Any non-zero, unclear, or unverified price -> `BLOCKED_COST_OR_AUTHORIZATION`.
- No explicit approval -> no external provisioning or activation.
- Missing/weak token or non-HTTPS public endpoint -> fail closed.
- Heartbeat without host identity/attestation -> not `PHYSICAL_VERIFIED`.
- Stale/replayed evidence -> quarantine.
- Simulation/CI evidence -> never accepted as persistent physical-node proof.
- Worker-reported shares without pool-side evidence -> mining outcome remains unverified.
