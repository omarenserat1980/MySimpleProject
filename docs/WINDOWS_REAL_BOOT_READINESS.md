# Windows real-boot contract readiness diagnostics

Run the manual **Brain Windows Contract Readiness (Secret-Safe)** GitHub Actions workflow to inspect the windows-real-boot environment and Control Plane prerequisites without displaying secret values or issuing a contract.

The authenticated GET endpoint /api/brain/windows/contracts/readiness returns only boolean secret-presence flags and whether the identity, checkpoint, leadership lease, and owner-approval files parse as JSON objects. It never returns secret values, file contents, keys, or approval payloads.

This is a preflight only. It does not verify owner-approval binding for a specific attempt, prove the leadership lease is current, consume approval, issue a contract, attest the executor, or prove Windows boot. A real boot attempt must still fetch a short-lived contract bound to GITHUB_SHA, GITHUB_RUN_ID, and GITHUB_RUN_ATTEMPT; verify signature and expiry; pass the trusted executor gates; and produce same-run installed-disk guest boot evidence.

The workflow prints only PRESENT/MISSING and safe status labels. Never log secret values, contract bodies, owner-approval payloads, or private key material.
