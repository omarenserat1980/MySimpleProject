# Electronic Brain — Changelog

## 2026-10-12

### Software-only execution enforcement
- Changed WorkerRegistry from software-first to software-only.
- Legacy device-adapter opt-in is ignored; physical/device/Termux/Android/hardware worker registration fails closed.
- Updated regression tests and operator documentation to reflect removal of device execution dependencies.
- Verification status is pending the pull-request CI result; this entry does not claim all workloads are already hardware-independent.

## 2026-10-01

### Runtime reliability
- Fixed Master Audit self-test invocation to run brain_v12.self_healing.self_test as a Python module.
- Fixed the independent Master Audit workflow invocation for the same package-import requirement.
- Added project specification, roadmap, decisions, and changelog documents.

### Evidence policy
- Distinguished source-file presence from runtime verification.
- Kept Quran registry status as an explicit runtime/build state rather than treating missing registry data as verified.

## Earlier work
- Added GitHub Cloud free Linux control plane.
- Added a bounded Brain Cloud task runner.
- Added Supervisor/self-healing, causal, Quran, media, and cinematic modules.
- Added evidence artifacts to important verification workflows.
