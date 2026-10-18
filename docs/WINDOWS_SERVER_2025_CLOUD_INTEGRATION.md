# Windows Server 2025 + Electronic Brain Cloud Integration

Status: **design and deployment runbook only — no VM has been provisioned or launched by this change**.

## Target architecture

- **Compute:** a provider-managed, licensed Windows Server 2025 image on a cloud VM. Do not redistribute a modified Windows ISO/VHDX; use the cloud provider's licensed image and terms.
- **Brain runtime:** the canonical `brain_v12` Python/FastAPI application, started with `python -m brain_v12.app` on the VM or on a separate Linux-compatible service if that is the lower-cost option.
- **Control plane:** GitHub repository and Actions for source, tests, deployment evidence, and rollback metadata.
- **Private connectivity:** outbound-only Tailscale/WireGuard or provider private network for administration and device-to-Brain traffic. Do not expose RDP (TCP/3389), WinRM, or the Brain API directly to the public internet.
- **Secrets:** provider secret store / protected GitHub environment secrets. Never commit API keys, RDP passwords, private keys, PayTabs credentials, or access tokens.
- **Evidence:** record provider VM ID, image/region, deployment revision, health-check results, timestamps, and rollback reference. A successful CI run alone is not proof that the VM booted or the service is reachable.

## Provisioning sequence

1. First seek a genuinely free option. If none meets requirements, stop and obtain explicit budget authorization before provisioning; verify Windows licensing plus compute/storage/network charges and set a budget cap.
2. Create the VM from the provider's official Windows Server 2025 image. Attach a managed OS disk and a least-privilege identity. Do not upload the local Hyper-V VHDX unless the provider explicitly supports that import and licensing path.
3. Restrict network access: no public RDP; establish private VPN access and allow only required egress. Keep the API bound to loopback until a private reverse proxy or private network endpoint is configured.
4. Install supported Python and Git on the VM, check out the approved repository revision, create a virtual environment, and install only the repository's pinned requirements.
5. Configure runtime state/data directories and secrets outside the repository. Run a smoke test against `/api/system/readiness` and relevant health endpoints.
6. Register a supervised Windows service only after the foreground smoke test passes. Use a dedicated non-admin service identity, automatic restart with bounded retries, and logs with secret redaction.
7. From a second machine on the private network, verify connectivity and authentication. Capture the VM state and evidence. Roll back if readiness fails.
8. Only report **LAUNCHED** after provider state is Running, Windows is reachable over the private channel, Brain readiness is healthy, and the deployed commit is recorded.

## Cost and resource guardrails

- Project constraint: zero budget and no paid Render. This runbook must not provision billable resources; if a fully free compliant Windows Server option is unavailable, stop and report the blocker rather than spending.
- The previously attempted Arkan Hyper-V host has about 3.7 GiB RAM and could not start the VM due to memory pressure. Do not treat it as a reliable production host.
- A Windows VM provides Windows execution; it does not magically add physical RAM/CPU to the Android phone or other devices.
- Keep the Brain API's existing authentication and readiness gates enabled. Never bypass `API_AUTH_FAILED` by disabling authentication.

## Acceptance gate

- [ ] Provider VM ID, region, official image reference, and billing estimate recorded
- [ ] VM provider state is Running
- [ ] Windows remote access works over private VPN only
- [ ] Brain service runs under a dedicated identity and survives a restart
- [ ] `/api/system/readiness` and media health checks pass from the intended network
- [ ] CI/deploy evidence records commit SHA and timestamps
- [ ] Rollback tested or documented
- [ ] No credentials or sensitive runtime state committed

Until every required runtime check is evidenced, the status remains **NOT LAUNCHED / NOT VERIFIED**.
