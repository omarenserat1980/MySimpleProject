# Brain Windows Server 2025 — Enhanced Cloud Node

## Purpose

Deliver a Brain-managed Windows Server 2025 cloud node by extending the official Windows Server 2025 guest with a secure Electronic Brain agent and operational controls. This is a customized server deployment and management layer, not a claim that Microsoft has released a different Windows edition or that the Windows kernel is being rewritten.

## Current baseline and deployment truth

- Target VM name: `brain-windows-2025`.
- Existing deployment workflow: `.github/workflows/brain-windows-cloud-launch.yml`.
- Existing verification script: `scripts/windows-cloud/verify.ps1`.
- Existing Brain enrollment guide: `brain_v12/WINDOWS_CLOUD_ONBOARDING.md`.
- A successful GitHub Actions job is not sufficient evidence of a deployed VM when the deploy step is skipped.
- The node must not be reported as available until Azure reports the VM running, guest inspection confirms 64-bit Windows Server 2025, and Brain receives a fresh authenticated heartbeat.

## Enhanced capabilities

1. **Brain enrollment and identity**
   - Use the existing Brain Windows Cloud enrollment flow.
   - Keep enrollment tokens short-lived and outside Git.
   - Reject stale or invalid heartbeat evidence.

2. **Secure task execution**
   - Accept only authenticated, authorized, explicitly scoped tasks from Brain.
   - Apply timeouts, bounded retries, allow-listed task types, and auditable results.
   - Do not expose an unrestricted remote shell or execute arbitrary prompts as administrator.

3. **Health and recovery**
   - Report OS version, boot time, agent health, disk and memory pressure, and last successful heartbeat.
   - Restart only the Brain agent when its health check fails; do not automatically reboot the host without an explicit policy.
   - Emit diagnostics before a task is marked failed.

4. **Secure administration**
   - Keep RDP and WinRM HTTPS restricted to the configured trusted source CIDR.
   - Never expose management ports to the entire internet.
   - Keep Azure credentials, administrator passwords, and enrollment secrets in approved secret stores.
   - Prefer Azure identity/OIDC and least-privilege permissions for provisioning.

5. **Evidence-first release gate**
   - Save deployment and guest-verification evidence as workflow artifacts.
   - Include workflow run ID, commit SHA, timestamp, VM resource ID, provisioning state, power state, guest OS identity, and heartbeat freshness.
   - Distinguish `PREFLIGHT_ONLY`, `DEPLOYMENT_FAILED`, `VM_RUNNING_GUEST_UNVERIFIED`, and `WINDOWS_CLOUD_AVAILABLE`.
   - The final available state requires a fresh Brain heartbeat and successful guest verification.

## Implementation sequence

- [ ] Inspect the latest cloud-launch run and confirm why deployment was skipped.
- [ ] Validate Azure environment variables, OIDC permissions, administrator secrets, trusted source CIDR, and cost/free-benefit review.
- [ ] Run preflight and retain its evidence.
- [ ] Provision/update the Azure VM only after explicit approval and cost review.
- [ ] Run the existing guest verification script and retain its JSON evidence.
- [ ] Enroll the VM with Brain using a short-lived token delivered securely.
- [ ] Verify `GET /api/brain/windows/cloud/status` reports `WINDOWS_CLOUD_AVAILABLE` and `verified: true`.
- [ ] Run bounded smoke tests for authenticated task dispatch, result reporting, heartbeat expiry, and agent recovery.
- [ ] Publish a final evidence summary linked to the run and commit.

## Acceptance criteria

The enhanced node is complete only when all of the following are evidenced:

- Azure VM exists and provisioning state is `Succeeded`.
- Azure power state is `VM running`.
- Guest inspection confirms 64-bit Windows Server 2025.
- RDP/WinRM network rules are restricted to the trusted source CIDR.
- Brain agent is enrolled and sends a fresh authenticated heartbeat.
- A harmless allow-listed smoke task completes and its result is recorded.
- A stale/missing heartbeat causes the node to be marked unavailable.
- Evidence artifacts can be reviewed and tied to the exact workflow run and commit.

## Cost and safety guardrails

- Do not create duplicate VMs or persistent cloud resources during preflight.
- Do not claim deployment success when provisioning or guest verification was skipped.
- Review the actual subscription-specific price/free-benefit eligibility before applying infrastructure changes.
- Stop on missing secrets, ambiguous Azure identity, broad management ingress, or failed verification.
- Do not store credentials, access tokens, or secret values in this document or workflow logs.
