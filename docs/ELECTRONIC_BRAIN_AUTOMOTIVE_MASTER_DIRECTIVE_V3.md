# ELECTRONIC BRAIN AUTOMOTIVE INTELLIGENCE PLATFORM — MASTER BUILD DIRECTIVE V3

## Mission
Build a local-first, independently testable automotive intelligence platform. Treat the phone, vehicle head unit, protocol bridge, simulator, and Brain services as separate components coordinated by explicit contracts. Deliver evidence-backed increments and a reproducible Android debug APK.

## Non-negotiable safety and governance
- Never modify `main` directly. Work only on `brain/automotive-intelligence-lab` and use reviewable commits/PRs.
- Never force-push, rewrite shared history, merge PR #1113, or overwrite a user worktree.
- Never flash firmware, root a phone/head unit, factory-reset a vehicle, alter USB gadget modes, bypass manufacturer protections, or send vehicle-control/CAN commands.
- No automatic APK installation, purchases, paid services, signing-key creation, secret printing, or secrets in Git.
- Keep VIN, OAuth tokens, private keys, certificates, and personal diagnostics out of source control. Redact identifiers from logs.
- Preserve upstream HeadSwap source, attribution, GPL-3.0 notices, and AGPL-3.0 notices for the relevant protocol files. Do not claim ownership of upstream work.
- Clearly distinguish simulated, phone-tested, head-unit-tested, and vehicle-tested evidence. Never infer compatibility from a successful build.

## Target architecture
1. Brain Automotive Core: orchestration, policy, capability registry, event bus, audit trail, local SQLite evidence.
2. HeadSwap Engine: isolated upstream CarLife 2.0 / Android Auto bridge; upstream changes minimized and recorded as reproducible patches.
3. Brain Adapter: versioned, narrow interface for lifecycle, connection state, diagnostics, and events; no invasive protocol fork.
4. Automotive Digital Twin: virtual head unit and deterministic USB/TCP/audio/video/touch test fixtures.
5. Fault Laboratory: controlled USB detach, packet loss, latency, reconnect, video-channel loss, audio-route loss, and malformed-frame tests.
6. Compatibility Registry: exact make/model/year/head-unit firmware/CarLife version, evidence level, limitations, and reproducible test ID.
7. Phone Client: Realme Android device as a thin membrane; no assumption that the native Brain shell emulator is full Termux.
8. Safety Guardian: read-only diagnostics by default, explicit consent for permissions, bounded resources, privacy-safe logs.
9. CI/QC: lint, unit tests, protocol tests, APK build, manifest permission audit, artifact checksum, SBOM/license inventory where feasible.
10. Operator Console: connection state, evidence, diagnostics, safe recovery guidance, and exportable redacted reports.

## Build sequence
A. Inspect repository state and upstream revision; record SHAs, licenses, dependencies, and unresolved tests.
B. Keep the Honda SQLite/network work and HeadSwap engine separately reviewable; do not fold unrelated changes into the bridge.
C. Build upstream HeadSwap in a separate Android project first. Apply only a reproducible Brain branding/application-id overlay; keep package identity side-by-side so the test APK does not overwrite the upstream app.
D. Run Gradle build and tests. Missing Android SDK components, certificates, or network access must be reported precisely; do not invent success.
E. Run virtual Head Unit/protocol tests, including known failure regression tests. A failing or skipped test blocks a green QC claim.
F. Add a narrow Brain adapter and evidence store only after protocol boundaries are understood.
G. Produce a debug APK with SHA-256, package name, version, build commit, and install/rollback instructions. Do not install it automatically.
H. Physical vehicle testing is manual and stationary. User confirms vehicle/head-unit model and uses the vehicle manufacturer's safe procedure. Never test while driving.

## Release gates
- Source and license audit complete.
- No secrets or VIN in tracked files.
- Manifest permissions justified and user-visible.
- Build reproducible from documented command.
- Tests reported individually; no hidden skipped/failing tests.
- APK exists, is non-empty, passes `apksigner verify`/`aapt dump badging` when tools are available, and SHA-256 recorded.
- Compatibility status remains `unknown` until verified on the exact head unit.

## Required deliverables
`docs/ELECTRONIC_BRAIN_AUTOMOTIVE_MASTER_DIRECTIVE_V3.md`, architecture and integration notes, upstream pin/license record, reproducible branding overlay, test report, APK artifact, checksum, and a PR-ready change summary.
