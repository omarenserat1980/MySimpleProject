# Brain Windows 2010 — Custom Experience on Windows Server 2025

## Product definition

**Brain Windows 2010** is the project name for Electronic Brain's customized Windows Server 2025 cloud environment. "2010" is a Brain product/version name, not an official Microsoft Windows edition. The underlying OS remains a properly licensed 64-bit Windows Server 2025 image; this project adds a Brain management layer, a custom web-based control center, and an AI task orchestration integration. It does not claim to replace or rewrite the Windows kernel.

## User-visible outcome

The user should be able to open the Brain Windows Control Center, see the real cloud VM's health and resource usage, ask Brain to run an approved task, and inspect task results and audit evidence. The experience must be usable from a phone as well as a desktop.

## Architecture

### 1. Base operating system and cloud lifecycle
- Target Azure VM name: `brain-windows-2025`.
- Use an official Windows Server 2025 x86_64 image and existing `.github/workflows/brain-windows-cloud-launch.yml` deployment workflow.
- Keep provisioning idempotent; inspect existing Azure resources before creating anything.
- Do not deploy until explicit approval and subscription-specific cost/free-benefit review are recorded.
- Existing verification script: `scripts/windows-cloud/verify.ps1`.

### 2. Brain Windows Control Center
Build a responsive web dashboard served through the existing Brain API/Web UI where possible. The interface should show:
- VM state: provisioning state, power state, OS build, last boot, and last verified heartbeat.
- Resource monitor: CPU, memory, disk capacity/free space, network activity, and process/service health when those metrics can be collected from the guest.
- Brain status: connected/disconnected, agent version, task queue, running/failed/completed tasks.
- Safe controls: refresh status, run an allow-listed diagnostic, restart the Brain agent, pause task intake, and view evidence.
- Clear states for unknown/stale data; never display fabricated or simulated readings as live measurements.
- Mobile-friendly layout and accessible status text.

### 3. Embedded Brain AI
- Route natural-language requests through the existing Brain orchestration/API, not directly into an unrestricted administrator shell.
- Convert requests into typed, permission-checked tasks with explicit input schema, timeout, resource budget, and expected output.
- Require approval for destructive actions, privilege changes, external network exposure, software installation, host reboot, and cloud resource creation.
- Record task intent, policy decision, execution identity, start/end times, exit status, and redacted output.
- Deny unsupported actions and report the reason; do not claim a task ran unless execution evidence exists.

### 4. Windows Brain Agent
- Enroll via the existing flow in `brain_v12/WINDOWS_CLOUD_ONBOARDING.md`.
- Keep enrollment tokens short-lived and out of source control.
- Send authenticated heartbeats and task results to the Brain Fabric endpoint over outbound HTTPS.
- Use a task allow-list, least privilege, bounded retries/timeouts, and a local audit trail.
- Collect OS identity, uptime, agent health, disk/memory pressure, and task status.
- On agent failure, collect diagnostics and restart the agent only if policy permits; host reboot remains approval-gated.

### 5. Security and access
- Use Azure identity/OIDC and least-privilege permissions for provisioning.
- Store admin credentials and tokens only in approved secret stores.
- Restrict RDP (TCP 3389) and WinRM HTTPS (TCP 5986) to the configured trusted source CIDR; never allow public-wide management ingress.
- Prefer the dashboard and agent's outbound HTTPS channel over opening additional inbound ports.
- Redact credentials and sensitive values from logs and artifacts.

### 6. Evidence and state model
- Persist deployment, guest verification, agent heartbeat, smoke-test, and task audit evidence as GitHub Actions artifacts or approved Brain evidence storage.
- Tie evidence to workflow run ID, commit SHA, timestamp, VM resource ID, and agent identity.
- Use explicit states: `PREFLIGHT_ONLY`, `DEPLOYMENT_FAILED`, `VM_RUNNING_GUEST_UNVERIFIED`, `VM_GUEST_VERIFIED_AGENT_PENDING`, and `WINDOWS_CLOUD_AVAILABLE`.
- `WINDOWS_CLOUD_AVAILABLE` requires Azure provisioning `Succeeded`, power state `VM running`, guest confirmation of 64-bit Windows Server 2025, safe management rules, successful agent enrollment, and a fresh authenticated heartbeat.
- Missing or stale heartbeat means unavailable. A green GitHub workflow with a skipped deploy step is not deployment evidence.

## Delivery plan

### Stage A — Verify current baseline
- [ ] Inspect latest cloud launch inputs and logs; identify why deploy was skipped.
- [ ] Check current Azure resources read-only to avoid duplicate infrastructure.
- [ ] Validate environment variables, OIDC, required secrets, allowed source CIDR, and cost review.
- [ ] Produce a preflight report without creating cloud resources.

### Stage B — Provision and verify the base VM
- [ ] After explicit deployment approval and cost review, provision/update the VM.
- [ ] Verify VM running and inspect the guest OS with the existing verification script.
- [ ] Save structured, redacted evidence linked to run and commit.

### Stage C — Connect Brain
- [ ] Enroll the guest using a short-lived token transferred securely.
- [ ] Verify authenticated fresh heartbeats and status endpoint `GET /api/brain/windows/cloud/status`.
- [ ] Exercise one harmless allow-listed diagnostic task end to end.
- [ ] Verify stale heartbeat, denied task, timeout, and agent-recovery behavior.

### Stage D — Build the Control Center
- [ ] Inspect existing FastAPI endpoints and UI before adding routes or duplicate dashboards.
- [ ] Add typed, authenticated endpoints for VM status, resource metrics, task submission, task history, and evidence.
- [ ] Implement the responsive dashboard using real API data, loading/error/stale states, and permission-aware controls.
- [ ] Add API and UI tests; verify mobile-sized layout and access control.

### Stage E — Release gate
- [ ] Run unit, integration, security, and end-to-end tests.
- [ ] Deploy the dashboard/agent only through the approved workflow.
- [ ] Confirm real VM, guest OS, agent heartbeat, resource telemetry, and task execution from evidence.
- [ ] Publish a release report; do not label the product production-ready if any mandatory gate is missing.

## Acceptance criteria

The first usable release requires:
1. Real Azure VM exists and is running Windows Server 2025 x86_64.
2. Brain status shows a fresh authenticated agent heartbeat.
3. Dashboard resource values come from live guest telemetry and indicate collection time.
4. One approved diagnostic task completes end-to-end with auditable evidence.
5. Unauthorized and destructive actions are denied or approval-gated.
6. RDP/WinRM ingress is restricted and no secrets are committed or logged.
7. Deployment and smoke-test evidence can be tied to exact run, commit, and VM.
8. When the VM or agent is unavailable, the dashboard says so accurately.

## Cost and safety guardrails

- Do not create duplicate VMs or persistent resources during preflight.
- Do not assume an Azure free benefit applies without checking the subscription.
- Do not expose management ports to the internet at large.
- Do not run arbitrary AI-generated PowerShell as administrator.
- Stop on missing credentials/configuration, unclear subscription identity, broad ingress, cost uncertainty, or failed verification.
- Never claim the VM, UI, AI integration, or deployment is complete until its acceptance evidence exists.
