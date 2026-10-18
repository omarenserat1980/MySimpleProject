# Cloud executor live-attestation worker

This is an opt-in, one-shot worker bootstrap for the intended cloud host. It
performs a signed challenge/attestation round trip against the Brain control
plane, validates the signature and host binding locally, and consumes the nonce
in the central registry. It does not execute arbitrary jobs and does not prove
ASIC connectivity or mining revenue.

## Required host-provisioned environment

- `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL`: HTTPS base URL of the Brain control plane.
- `BRAIN_CLOUD_EXECUTOR_TOKEN`: enrolled executor token, injected by the host secret manager.
- `BRAIN_CLOUD_EXECUTOR_ID`: exact enrolled executor ID.
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64`: trusted Ed25519 public key provisioned out of band.

The Brain control plane must separately have its signing key, enrollment hash
inventory, trusted hostname/architecture binding, and central registry configured.
The hostname binding must match `socket.gethostname()` on the worker. The
worker supports x86_64/amd64 only, matching the current server-side policy.

## Run

From the repository root on the intended host, with the project's Python
dependencies installed:

```sh
python -m brain_v12.tools.cloud_executor_attestation_worker
```

Exit code 0 and `LIVE_ATTESTATION_VERIFIED` mean the signed round trip and
central nonce consumption succeeded for that host at that time. Exit code 1
means no successful live proof was established. The output intentionally omits
tokens and signed payloads.

Do not put secrets in the repository, command-line arguments, browser storage,
or CI logs. This worker is not evidence of a deployed worker until it is run on
the intended host and its result is independently reviewed.
