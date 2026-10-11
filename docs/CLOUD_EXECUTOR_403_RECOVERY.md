# Cloud Executor Attestation 403 Recovery

Use this when the real-boot workflow reports `CLOUD_EXECUTOR_HTTP_403:CLOUD_EXECUTOR_AUTH_REJECTED` from `POST /api/cloud-executor/attestation/challenge`.

A 403 means the supplied token does not match the enrollment digest for the exact executor ID, or that the ID has no valid digest entry. A missing host binding is a separate 503 error. Do not disable authentication or bypass attestation.

## Safe recovery sequence

1. Read the exact `BRAIN_CLOUD_EXECUTOR_ID` from the trusted runner host configuration. Do not guess or rename it.
2. Confirm the same raw token is set in the runner host variable `BRAIN_CLOUD_EXECUTOR_TOKEN` and protected GitHub Environment secret `BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED`. Do not print either value.
3. In a trusted local terminal, run:

   ```sh
   python tools/hash_cloud_executor_token.py --executor-id "EXACT_EXECUTOR_ID"
   ```

   Paste the existing token into the hidden prompt. The helper prints only the executor ID and SHA-256 digest. Never pass a token as a command-line argument.
4. Merge the resulting digest entry into the Control Plane's `BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON` JSON object, preserving other executor entries. The key must exactly match the configured executor ID; the value must be the lowercase SHA-256 hex digest of the token's UTF-8 bytes.
5. Confirm `BRAIN_CLOUD_EXECUTOR_HOST_BINDINGS_JSON` has a trusted entry for the same ID with the authorized runner's actual hostname and `x86_64` architecture.
6. Redeploy the Control Plane if required, then rerun the attestation gate. Continue only after challenge, issue, and consume succeed. A Windows Server 2025 boot still requires guest-generated evidence and the independent completion gate from the same run.

This helper does not contact GitHub or Render and does not change any secret. Never paste raw tokens, private keys, or full environment dumps into chat, issues, commits, workflow logs, or artifacts.
