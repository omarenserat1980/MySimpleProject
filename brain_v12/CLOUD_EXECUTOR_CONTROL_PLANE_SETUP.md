# Brain Cloud Executor Control-Plane Setup

This runbook configures the issuer **on the Brain control-plane host**, not on Arkan's runner process and not in GitHub Actions. It does not deploy anything automatically. Do not paste secrets into chat, a GitHub issue, a commit, or workflow logs.

## 1. Deploy the central API

Deploy the branch containing `brain_v12/brain/cloud_executor_attestation_api.py` and mount `cloud_executor_attestation_router` in `brain_v12/app.py`. Expose the API only through a trusted HTTPS endpoint. Keep one authoritative Brain API/database for all executor requests; all hosts must consume against the same durable SQLite database on the Brain control-plane host. Do not copy the registry database to runners or use isolated local copies.

Set:
- `BRAIN_CLOUD_EXECUTOR_REGISTRY_DB` to a durable control-plane database path (or deliberately use the Brain `BRAIN_DB`).
- `BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64` from a protected secret manager or a root-controlled systemd `EnvironmentFile`.
- `BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON` to a JSON object mapping each enrolled executor ID to the SHA-256 hex digest of that executor's high-entropy bearer token.

The API rejects unknown executor IDs and compares token digests in constant time. It does not accept a general Brain control key as a substitute for per-executor enrollment.

## 2. Create the signing key on the control-plane host

Run as root on the trusted Brain control-plane host only. This command stores the private key in a root-only environment file and prints only the public key and its SHA-256 fingerprint. Do not run it on a runner or in CI.

```bash
sudo install -d -o root -g root -m 0700 /etc/brain/secrets
sudo python3 - <<'PY'
import base64, hashlib, os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

key = Ed25519PrivateKey.generate()
private = base64.b64encode(key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)).decode("ascii")
public_bytes = key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
public_b64 = base64.b64encode(public_bytes).decode("ascii")
env_file = Path("/etc/brain/secrets/cloud-executor-attestation.env")
env_file.write_text("BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64=" + private + "\n", encoding="utf-8")
os.chmod(env_file, 0o600)
print("PUBLIC_KEY_B64=" + public_b64)
print("PUBLIC_KEY_SHA256=" + hashlib.sha256(public_bytes).hexdigest())
PY
```

Install the env file into the trusted Brain API service's systemd unit using an `EnvironmentFile=/etc/brain/secrets/cloud-executor-attestation.env` override, then restart that service through the normal approved deployment process. Verify the running service has the key without printing it. Back up the private key only through the approved secret-backup process. Key rotation requires a coordinated overlap/migration plan; do not replace the trust key without updating executor hosts.

## 3. Enroll one executor

Choose the exact stable `BRAIN_CLOUD_EXECUTOR_ID` that the host will use. Generate a high-entropy token on a trusted management machine, store only its SHA-256 digest in the control-plane enrollment map, and deliver the raw token to the host through a separate secure channel.

Example digest generation (the token itself must not be printed to CI logs):
```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
printf '%s' "$EXECUTOR_TOKEN" | sha256sum
```

Configure `BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON` with the resulting digest map. Inject the raw token on the host as `BRAIN_CLOUD_EXECUTOR_TOKEN` only for bootstrap. Never put it in the repository, the runner `.env`, or workflow variables. Rotate it after suspected exposure.

## 4. Install and verify the trust anchor on the executor

Transfer `PUBLIC_KEY_B64` and its fingerprint through trusted host-management channels. Confirm the fingerprint independently (for example, by comparing it with the control-plane operator's separately recorded value), then install:

```bash
printf '%s' "$PUBLIC_KEY_B64" | sudo env BRAIN_TRUST_ANCHOR_SHA256="$PUBLIC_KEY_SHA256" tools/install_brain_executor_trust_anchor.sh
sudo stat -c '%U %G %a %n' /etc/brain/trust/cloud-executor-attestation-ed25519.pub.b64
sha256sum <(base64 -d /etc/brain/trust/cloud-executor-attestation-ed25519.pub.b64)
```

Expected owner is root and the key file must not be writable by group/other. Compare the final fingerprint with the independently confirmed fingerprint. Do not trust a fingerprint delivered only alongside the key.

## 5. Run the one-job bootstrap

On the executor host, set:
- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID` to the enrolled ID
- `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL=https://<trusted-brain-api>`
- `BRAIN_CLOUD_EXECUTOR_TOKEN` through the host's secret-injection mechanism
- a short-lived runner-registration token supplied by the trusted operator; the runner account must not have access to the operator's saved GitHub CLI credentials

The host must also be Linux x86_64 with usable KVM, QEMU, OVMF, and all listed image tools. Run `tools/bootstrap_brain_cloud_executor.sh` from the checked-out repository as a dedicated unprivileged account. The operator must obtain the short-lived GitHub runner-registration token outside that account and inject it as `BRAIN_GITHUB_RUNNER_REGISTRATION_TOKEN`. The script must not call `gh` or read the operator's saved GitHub CLI credentials. It clears the injected registration token before starting the job, fetches and verifies a fresh Brain proof, consumes it centrally, and starts an ephemeral runner for one job. Verify the runner account cannot read the operator's home directory or credential files.

Do not run the bootstrap on Arkan or Redmi until the trust anchor and control-plane settings are independently configured. This runbook has not been executed on any host in this change.

## 6. Acceptance evidence

Before considering merge:
1. Capture redacted control-plane configuration evidence (never secrets).
2. Record the public-key fingerprint independently and verify the installed host file's ownership/mode/hash.
3. Run the preflight on the actual Linux x86_64/KVM host and preserve the gate evidence outside the ephemeral runner workspace.
4. Confirm a second consume attempt for the same nonce is rejected by the central API.
5. Review every required CI workflow at the exact latest PR head.
6. Separately verify Windows Server 2025 boot evidence. Attestation and KVM checks do not prove Windows booted.

Until all six acceptance points are independently evidenced, keep PR #278 in draft and unmerged, and do not enable Windows Real Boot.
