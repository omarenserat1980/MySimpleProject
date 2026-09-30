# Brain Cloud-only runtime policy

Brain production runtime is cloud-native and device-independent.

## Rules

- The production Brain runtime is **Brain Cloud**.
- Android, phone storage, standalone Termux, and external Termux agents are optional clients only and are never required.
- Production orchestration, cinematic rendering, FFmpeg/QC, state, queues, and long-running workers execute in the cloud runtime.
- No production workflow may require `TERMUX_AGENT_KEY`, `TERMUX_AGENT_KEY_SHA256`, a Termux executable, a phone SSH key, or a phone/VPS deployment script.
- The Android client must not contain a Termux deployment bridge.
- Cloud deployment is performed by the cloud host/GitHub deployment workflow, not by a phone.
- A cloud host is still required for a long-lived Brain Cloud service; this repository does not silently create a paid cloud account or VM.

Runtime identity:
`BRAIN_CLOUD_MODE=cloud-only`
`BRAIN_DEVICE_EXECUTION_ENABLED=0`
`BRAIN_TERMUX_REQUIRED=0`


## Enforced CI guard

The repository provides `brain_v12/self_healing/cloud_only_guard.py` and the continuous verification workflow runs it. The guard rejects production files/workflows that introduce forbidden Termux/phone deployment requirements, while allowing legacy documentation and optional client tooling.
