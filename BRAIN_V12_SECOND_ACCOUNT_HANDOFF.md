# Electronic Brain V12 — Second-Account / New-Repository Handoff

## Mission
Rebuild/continue the Electronic Brain V12 project in a new ChatGPT account and a different GitHub repository without losing any previously implemented or proposed capability. Preserve the Redmi3 Termux agent as a first-class device integration.

## Source of truth discovered
Current source repository: `omarenserat1980/MySimpleProject`
Default branch: `main`
Current inspected source revision: `90f2e68df338b2a0d47775a272c69b49196a778e`

The repository README identifies `brain_v12/` as the V12 core, Arabic RTL UI, the cognitive loop, Brain Cloud runtime, independent media QC, and Mining Economics analysis. Do not remove existing capabilities during migration.

## Required architecture
- Brain V12 is the decision/reasoning/orchestration layer.
- GitHub is the durable source/code storage and version-control tool.
- Cloud runtime is the production execution environment.
- Termux/Android is an optional authorized execution agent; it must not become the production dependency.
- Redmi3 agent ID: `redmi3-01`.
- Redmi3 key file: `~/v12-agent/agent.key`.
- Preserve the agent polling/execution protocol and authentication design.
- Do not silently register or reactivate the old device as a replacement for Redmi3.

## Cognitive loop
PERCEIVE → UNDERSTAND → MEMORY → GOAL → PLAN → OPTIONS → DECIDE → ACT → OBSERVE → EVALUATE → LEARN

## Existing capability families to preserve and verify
- cognition / memory / decision / tasks / permissions
- plugins / AI Gateway / ChatGPT integration
- code-agent and code-tool capability
- self-healing and verification gates
- Brain Cloud worker/runtime
- cinematic/media pipeline with real MP4 creation and independent FFprobe/QC
- FFmpeg/FFprobe Brain-native toolchain variables
- research/economic/opportunity analysis
- Mining Economics calculation layer; analysis only, never claim actual income without verifiable payment evidence
- Arabic RTL control UI and real runtime status
- GitHub code inspection, backup, validation and controlled change workflow
- device/Termux agent gateway
- YouTube OAuth integration and encrypted token storage where already implemented

## YouTube OAuth configuration
Production callback previously established:
`https://electronic-brain-v12-gwwg.onrender.com/api/youtube/oauth/callback`

Existing variable names:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`
- `YOUTUBE_TOKEN_ENCRYPTION_KEY`

Never put secrets in GitHub or in chat. Existing Google Client ID/Secret should be reused when available; do not create unnecessary duplicates.

## Previous production context
Render service previously used:
`electronic-brain-v12-gwwg`
Service ID:
`srv-dapmmp0473hc73c9ceog`

Historical health contract:
`GET /health` should return an OK Brain V12 response and expose the active systems/version. Do not trust a green UI alone: verify runtime endpoints and deployment state.

## Migration rules
1. Clone/inspect the complete source before changing architecture.
2. Inventory every directory, API route, worker, agent, test, workflow, deployment file and integration.
3. Reconcile duplicates before deleting anything.
4. Preserve behavior first; improve implementation second.
5. Never replace a working capability with a visual mock or offline placeholder.
6. Never claim a feature is live until source, build, deployment and runtime evidence agree.
7. Secrets remain provider-side only.
8. Keep Redmi3 support even if cloud execution is preferred.
9. Do not depend on the old Render service for the new deployment; the new project must have its own deployment configuration.
10. Maintain a rollback path at every consequential migration step.

## Verification gates
For every migration stage:
- repository builds/compiles
- tests pass or failures are explicitly classified
- health endpoint responds
- core API status responds with real runtime data
- authentication/permissions are exercised
- agent authentication is tested using `redmi3-01`
- media pipeline creates a real artifact and runs FFprobe/QC when applicable
- deployment logs are inspected
- production URL is tested after deployment
- only then mark the stage complete

## Target execution order
### Stage 1 — Inventory
Audit source tree, dependencies, environment variables, API routes, tests, workers, GitHub Actions, Render configuration, media pipeline, YouTube integration, and Termux/Android agent files.

### Stage 2 — Migration baseline
Create the new repository from the verified source baseline. Preserve history where practical. Add a migration manifest containing the source commit and capability inventory.

### Stage 3 — Core runtime
Boot `brain_v12.app`, verify health, status, cognitive loop, memory, decision, permissions, tasks and code tooling.

### Stage 4 — Agent gateway
Restore `redmi3-01`; verify key-based authentication, polling, command execution, result return and Brain-side verification. Do not require the old device.

### Stage 5 — Cloud workers
Restore worker registration, heartbeat, queues, leases, duplicate protection and scheduled jobs. Verify cloud-first behavior.

### Stage 6 — Media/cinematic system
Restore Brain-native FFmpeg/FFprobe configuration and real MP4/QC gates. No fake success state.

### Stage 7 — YouTube
Restore OAuth routes and encryption configuration. Verify readiness and callback using the new deployment URL when the project is migrated. Do not expose credentials.

### Stage 8 — UI
Restore Arabic RTL UI, then connect every dashboard value to real APIs. Remove stale/offline visual-only states.

### Stage 9 — Self-healing and code-agent loop
Brain plans → GitHub stores code → controlled executor applies changes → tests run → Brain observes evidence → Brain decides whether to accept/rollback/escalate.

### Stage 10 — Production acceptance
Run the full audit, deployment verification, endpoint smoke tests, agent test, integration tests and rollback test. Record exact commit, deployment, URL and test evidence.

## Non-negotiable safety/quality rules
- No destructive mass deletion during migration.
- No hard-coded secrets.
- No fabricated revenue.
- No fabricated runtime status.
- No automatic irreversible production changes merely because a plan says so.
- Preserve user authorization boundaries and auditability.
- When a provider limitation blocks a stage, record the exact blocker and continue all independent stages rather than pretending it succeeded.

## First instruction to the new ChatGPT account
Treat this file and the migrated repository as the working technical baseline. Start with an evidence-based inventory, reconstruct the current architecture, preserve all existing capabilities, and execute the stages above continuously wherever the connected tools and permissions allow. Do not ask the user to repeat information already present in this handoff.
