# Electronic Brain — Arkan Compute Pool Completion Prompt

## Mission
Complete the existing device-backed software cloud pool in omarenserat1980/MySimpleProject without replacing its architecture or claiming physical resources that have not been observed.

## Required execution
1. Continue from PR #405 branch brain-software-cloud-pool; inspect its diff and CI before changes.
2. Keep the pool zero-cost and fail-closed. Do not provision paid services, alter secrets, register accounts, or run privileged/destructive commands.
3. Measure the Brain host CPU, RAM, and free disk from the actual runtime.
4. Observe an enrolled Windows executor with ID prefix windows-executor-. Online status requires a recent authenticated heartbeat within configured TTL. Capacity must come from heartbeat metadata, not invented values.
5. Add a Windows PowerShell agent for Arkan that gathers real host measurements and posts authenticated heartbeats to POST /api/device/heartbeat. Require operator-supplied API URL and agent key via environment variables. Do not hard-code credentials or execute arbitrary tasks.
6. Add tests for live Windows heartbeat, stale heartbeat, missing measurements, and zero-cost scheduling.
7. Expose GET /api/cloud-pool/status and accurately distinguish host-only from remote-node-observed.
8. Run targeted tests and existing CI. Do not merge a draft PR automatically.
9. Save changes on the same PR branch and report exact commit, test run, and remaining manual action.

## Acceptance gate
Arkan is NOT declared an active compute node until the script runs on the physical ASUS device, an authenticated heartbeat appears in the control plane, measured resources appear in the status API, and a safe test task is successfully executed and verified. Green CI only proves code behavior in CI.