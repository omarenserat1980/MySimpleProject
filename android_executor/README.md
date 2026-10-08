# Electronic Brain — PHONE-ONLY Android Executor

Native Android executor for Electronic Brain. This module is designed to remove the manual dependency on Termux for the control/bridge layer.

## Current v1 capabilities

- Polls the Electronic Brain device API over HTTPS.
- Reports execution results back to the Brain.
- Android foreground service for persistent execution.
- Device/platform/status probes.
- File operations restricted to:
  `/storage/emulated/0/Movies/ElectronicBrain/`
- Safe path traversal protection.
- Basic Toybox command adapter with an explicit allowlist.
- GitHub Actions workflow that builds a debug APK.
- Automatic Brain Runtime bootstrap when the local Brain health endpoint is unavailable.
- Explicit `brain_runtime_launch` execution task backed by the Termux bootstrap bridge.

## Important

This is the first native executor layer, not a full Linux distribution. FFmpeg, Python and local AI runtimes are separate adapters to be integrated next.

## Brain protocol

Poll:
`GET /api/device/poll?agent_id=<id>`

Header:
`X-V12-Agent-Key: <key>`

Report:
`POST /api/device/report`

The executor deliberately rejects commands outside its allowlist. Executor completion is not the same as factory verification; the Brain must perform the required evidence/QC checks before marking an operation VERIFIED.

## Build

Open `android_executor/` in Android Studio, or use the included GitHub Actions workflow to build `app-debug.apk`.

## CI verification

The Android Executor CI workflow is the authoritative build path for the debug APK. A successful workflow without the uploaded APK artifact is not treated as a completed build.

**CI release trigger:** this revision intentionally updates the Android Executor module so the path-filtered CI workflow executes against the current `main` head, including the runtime-bootstrap fixes. Do not reuse pre-fix APK artifacts for runtime verification.
