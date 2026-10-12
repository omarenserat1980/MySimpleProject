# GitHub Secret Description: `BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED`

## Purpose

A per-executor bearer credential used by the Electronic Brain cloud executor to authenticate with the trusted Brain Control Plane's cloud-executor attestation registry.

## Where it belongs

- GitHub repository: `omarenserat1980/MySimpleProject`
- GitHub Actions Environment: `windows-real-boot`
- Secret name: `BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED`

This is an **Environment secret**, not a repository variable and not a public configuration value. Do not create a repository-level duplicate.

## How the credential is validated

The trusted Control Plane identifies the enrolled executor and compares the SHA-256 digest of the presented token with the digest stored for that executor ID in `BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON`. The raw token must be delivered to the executor and GitHub Environment through approved secret-handling channels.

The token is not interchangeable with a GitHub Personal Access Token, a general Brain API key, a signing key, or a Windows contract-delivery key.

## Required safety properties

- Use a high-entropy token dedicated to one approved executor.
- Store only the token's SHA-256 digest in the Control Plane enrollment map.
- Never commit the raw token, print it in workflow logs, or paste it into chat or an issue.
- Never use a placeholder or an un-enrolled token.
- Rotate the token through the approved process if exposure is suspected.
- GitHub does not reveal the saved secret value; audit its name/presence only.

## Related Environment secrets

The `windows-real-boot` Environment also requires:

1. `BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED`
2. `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED`
3. `BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED`
4. `BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED`

See [Windows Real-Boot Secret and Host Matrix](WINDOWS_REAL_BOOT_SECRET_MATRIX.md) and [Cloud Executor Control-Plane Setup](../brain_v12/CLOUD_EXECUTOR_CONTROL_PLANE_SETUP.md).

## What the presence of this secret proves

The existence of the secret name proves only that GitHub has a named Environment secret. It does **not** prove that its value matches the enrolled digest, that the Control Plane is reachable or trusted, that an executor is enrolled, that a contract is valid, or that Windows Server 2025 booted.

Real-boot acceptance requires fresh attestation/contract verification and guest-generated boot evidence from the same workflow run.
