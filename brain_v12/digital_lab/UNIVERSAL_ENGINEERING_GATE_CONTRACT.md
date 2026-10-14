# Brain Digital Lab — Universal Engineering Gate Contract

Status: proposed implementation contract; acceptance depends on passing repository CI.
Budget: zero. Use existing repository code and free/open-source tooling only.
Scope: Electronic Brain V12/V13 software, scripts, apps, agents, APIs, ASIC/RTL assets, device bridges, virtual hardware, servers, infrastructure, media and business workflows.

## 1. Mandatory intake

Every discovered asset must have a stable repository-relative `asset_id`, owning domain, source revision, lifecycle state, verification state, risk class, and evidence references. Discovery metadata is not runtime evidence. External and physical assets must be represented separately from repository files.

## 2. Required lifecycle

`DISCOVERED_NOT_TESTED → IN_REVIEW → TESTING → ACCEPTED | REJECTED | BLOCKED`

- `ACCEPTED` requires passing tests and evidence tied to the exact asset/version and execution attempt.
- `REJECTED` requires a recorded failing check and evidence.
- `BLOCKED` means a required dependency, permission, runner, secret, device, service, or independent verifier is unavailable.
- `NOT_RUN` must remain explicit when no test ran. Never translate missing evidence into PASS.
- Revisions invalidate evidence whose source revision or artifact digest no longer matches.

## 3. Evidence record minimum

Each evidence record should contain:
- source/tool and version;
- repository commit or immutable asset identity;
- execution/run URL or local log path;
- UTC observation time and result;
- command/check identifier and exit status;
- artifact path/URI, size and SHA-256 where applicable;
- scope and limitations of what the check proves.

Secrets, tokens, payment credentials, private customer data, and personal data must not be written into evidence artifacts.

## 4. Domain-specific checks

| Domain | Minimum checks before acceptance |
|---|---|
| Python/software modules | focused tests, regression tests, static checks where configured, import/CLI smoke test |
| Scripts/automation | syntax validation, safe-path checks, dry-run or bounded fixture test; no destructive execution by default |
| API/services | unit/integration tests, auth and permission checks, health/readiness response, failure-path tests |
| Apps/UI | build/test evidence and install/launch or browser smoke test in an available environment |
| Agents/devices | authenticated identity, freshness timestamp, capability allowlist, bounded task, observed result; simulator evidence must be labeled simulated |
| ASIC/RTL | lint/elaboration, functional tests, formal checks when available, synthesis and physical-design reports, GDSII structural validation and checksums |
| Virtual hardware/servers | configuration validation, boot evidence from the guest, guest-origin health checks, and a reachable endpoint; build success alone is not boot proof |
| Media pipeline | output existence, probe/codec/duration checks, content-level QC and manifest integrity |
| Payments/revenue | provider-side live transaction evidence, matching order/payment identifiers, delivery evidence and reconciliation; sandbox tests are not real revenue |
| Infrastructure/deployment | configuration validation, deployment/run identity, endpoint health and rollback evidence |

Unavailable tools or infrastructure must produce `BLOCKED` or `NOT_RUN`, not fabricated evidence.

## 5. Universal release gate

A release may proceed only when:
1. the tested source revision is known;
2. required checks for the affected domains completed successfully;
3. each accepted asset has evidence matching its current revision;
4. no required check is `FAIL`, `BLOCKED`, or `NOT_RUN`;
5. test output and evidence manifest are uploaded or stored durably;
6. the release summary states exactly what was and was not proved.

The gate must fail closed on missing, malformed, stale, or mismatched evidence. A metadata inventory is not a certification that all assets are alive or healthy.

## 6. Safety and change control

- No paid resources, paid reservations, cloud upgrades, or foundry submissions.
- No direct changes to `main`; use a reviewable branch and pull request.
- Do not auto-merge. Require human review and passing checks.
- Do not execute arbitrary discovered files or shell commands merely because they are inventoried.
- Preserve `LEGACY_REQUIREMENTS` and `TODO_FROM_LEGACY`; additions must not silently delete legacy requirements.
- For hardware claims, separate RTL simulation, synthesis, physical design, foundry signoff, fabrication, and tested physical silicon as distinct evidence levels.

## 7. Initial implementation sequence

1. Run the existing inventory generator and validator and preserve its JSON artifact.
2. Confirm tests enforce evidence requirements for `PASS`, `FAIL`, `ACCEPTED`, and `REJECTED`.
3. Add per-domain adapters that call existing test/health tools rather than duplicate them.
4. Bind evidence to commit, attempt, and artifact digest.
5. Gate pull-request acceptance on required checks and publish a concise machine-readable summary.
6. Add runtime/device/server checks only when an authorized target and trustworthy credentials are available.
7. Expand one domain at a time; never mark untested domains accepted.

This contract describes intended governance. It does not by itself prove that any component has passed or that every domain adapter is implemented.
