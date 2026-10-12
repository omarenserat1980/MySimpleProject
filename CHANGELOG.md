# Electronic Brain — Changelog

## 2026-10-12

### Software-only execution foundation
- Changed the existing worker registry to default to software nodes and require explicit opt-in for physical-device worker discovery.
- Isolated failures from optional DeviceBridge adapters so they do not break software-node registry operations.
- Added regression tests for default-off device adapters, explicit opt-in, lease expiry, invalid worker IDs, and adapter failure isolation.
- Added a GitHub-hosted Ubuntu workflow for focused software-node verification and documented the incremental migration boundary.
- Verification is pending the actual GitHub Actions result; this changelog entry does not claim the tests have passed or the full repository has become hardware-independent.

## 2026-10-01

### Runtime reliability
- Fixed the Master Audit self-test invocation to run brain_v12.self_healing.self_test as a Python module.
- Fixed the independent Master Audit workflow self-test invocation for the same package-import requirement.
- Added the core project specification, roadmap, decisions, and changelog documents required by the evidence audit.

### Evidence policy
- Continued the distinction between source-file presence and runtime verification.
- Kept Quran registry status as an explicit runtime/build state rather than treating missing registry data as verified.

## Earlier work
- Added the GitHub Cloud free Linux control plane.
- Added a bounded Brain Cloud task runner.
- Added Supervisor/self-healing, causal, Quran, media, and cinematic modules.
- Added evidence artifacts to important verification workflows.
