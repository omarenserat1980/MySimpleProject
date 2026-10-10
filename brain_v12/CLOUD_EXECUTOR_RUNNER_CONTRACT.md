# Brain Cloud Executor Runner Contract

This contract defines the only runner class allowed to execute Windows Real Boot.

## Required GitHub labels

- self-hosted
- linux
- x64
- brain-internal
- qemu
- windows-real-boot
- brain-cloud-executor

## Required runner-provided identity

The runner host/service environment must provide:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID=<stable-or-ephemeral executor identity>`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE=<path to signed JSON attestation>`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64=<trusted Ed25519 public key>`

The attestation file and trust anchor must be provisioned out of band by the trusted Brain/control-plane issuer. Never generate the production signing key in GitHub Actions or on the executor. Never place the private key on the runner.

The verifier requires schema `brain.cloud-executor-attestation.v1`, a matching executor ID, audience `brain-cloud-executor`, a nonce, issue/expiry times with a maximum one-hour validity, and a valid Ed25519 signature over the canonical document fields. The public key must be provisioned through a trusted host-management channel; an environment variable alone is not a trust-root distribution strategy.

## Required substrate

The runner must independently provide:

- x86_64
- `/dev/kvm` readable and writable by the runner
- `qemu-system-x86_64` and `qemu-img`
- working KVM acceleration
- QEMU/OVMF and the Windows workflow toolchain
- writable execution and evidence directories

The bootstrap checks architecture, KVM permissions, required tools, OVMF, and the signed-attestation Cloud Executor Gate **before** downloading/configuring/registering the GitHub runner. A failed preflight must not leave a newly registered runner behind.

## Lifecycle

The preferred production lifecycle is:

`PROVISION -> SIGNED ATTESTATION -> PREFLIGHT -> REGISTER JIT/EPHEMERAL -> ONE JOB -> PRESERVE EVIDENCE -> DEREGISTER -> DESTROY`

A cloud VM being created or a GitHub runner being online is not capability evidence. The signed attestation establishes only the executor identity claims covered by the trusted issuer; it does not prove Windows booted.

## Gate

`brain_v12/brain/cloud_executor_gate.py` must return `verified=true` before Windows Real Boot can start. The gate combines signed identity validation with x86_64, KVM, QEMU, and writable-surface checks. It is not a Windows boot completion gate.

## Security rules

- Never set Cloud Executor identity in workflow YAML.
- Never print registration tokens, private keys, owner approvals, or attestation contents.
- Never create or sign the Windows execution contract inside the workflow.
- Do not start Windows Real Boot unless the separately issued Brain execution contract passes its closed-loop verification gate.
- Preserve evidence and keep boot completion distinct from substrate-gate success.


## Trusted issuer, trust anchor, replay, and renewal

- `brain_v12/brain/cloud_executor_attestation_issuer.py` is a control-plane library, not a public HTTP endpoint. It creates a server-generated challenge with a 60-second TTL and consumes it atomically once before signing. It must only be called behind an authenticated identity adapter; this module alone does not authenticate a network caller.
- The issuer private key is supplied by a secret manager or protected control-plane injection as `BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64`. It must never be present on the runner, workflow YAML, repository, or logs. CI tests use ephemeral test keys only.
- Install the public key using `tools/install_brain_executor_trust_anchor.sh` from an independent trusted host-management channel. Confirm its SHA-256 fingerprint separately. The installer has not been run on Arkan or Redmi.
- The host gate consumes each verified nonce in a persistent SQLite ledger at `/var/lib/brain/cloud-executor-attestation-nonces.sqlite3` by default. Keep it outside the ephemeral runner workspace. Multi-host deployments need a centralized atomic replay registry; separate local ledgers do not prevent cross-host replay.
- Renewal policy: new unpredictable server-generated challenge per preflight; challenge TTL 60 seconds; attestation TTL at most 300 seconds; single-use challenge and nonce. Renew by obtaining a new challenge and issuing a new attestation, never by extending an old one.
- **Deployment gate remains closed:** the authenticated network adapter, production secret-manager binding, and cross-host replay registry are not provisioned here. Do not expose the issuer or run Windows Real Boot until these are implemented and independently reviewed.
