# Electronic Brain — الكسا (Alksa) Independent Cloud

## Identity and independence

**Cloud name:** الكسا  
**Internal slug:** `alksa`  
**Primary backend:** OpenNebula + KVM/QEMU  
**Arkan dependency:** none

This cloud must be deployable and operable without Arkan. Arkan is not the cloud host, hypervisor, bootstrap machine, GitHub Actions runner, executor, or a required network hop. Do not register or depend on the Arkan Desktop Commander device. Cloud health must be measured from the chosen Linux/OpenNebula host and the Windows guest itself.

The previous Arkan-dependent device cloud-pool proposal, PR #405, has been retired and closed. Do not revive or merge that proposal as the implementation for الكسا. Closing that PR does not delete its remote branch or remove any previously merged files; this change only retires that unmerged proposal.

If no independent Linux x86-64 host is available, deployment remains blocked; do not silently route work through Arkan or claim the cloud is running. GitHub Actions can validate code but does not substitute for the real cloud host.

## Decision

Use the already-integrated OpenNebula provider as the primary self-hosted cloud backend. Keep the existing Windows Cloud Executor, provider factory, guest verification gate, and Azure/Terraform adapter. Do not create a second cloud implementation or silently fall back to a paid provider.

This design uses open-source OpenNebula + KVM/QEMU on a Linux x86-64 host. Cloud software is not a substitute for physical CPU, RAM, disk, or a reachable hypervisor.

## Deployment stages

1. **Choose a real host independent of Arkan**: Linux x86-64, hardware virtualization enabled, at least 8 GiB RAM and 40 GiB free disk for a minimal lab; 16 GiB+ RAM is strongly preferred for a Windows Server guest. These are conservative project preflight thresholds, not vendor minimums.
2. **Install OpenNebula**: follow the official installation guide for the chosen supported Linux release. Configure a frontend and KVM node; do not paste secrets into repository files.
3. **Verify host virtualization**: `/dev/kvm` must exist and be accessible to the OpenNebula/KVM service account.
4. **Configure CLI access**: install `onevm` and `onetemplate`; configure `ONE_XMLRPC` and `ONE_AUTH` in the host's protected environment or OpenNebula CLI config. Never commit credentials.
5. **Create/import a Windows Server 2025 template**: use authorized installation media and a suitable virtual network and datastore. Respect Microsoft licensing and evaluation terms.
6. **Run the read-only preflight**:

   ```bash
   python3 brain_v12/tools/opennebula_cloud_preflight.py
   ```

   A nonzero exit code means a required check is blocked. Resolve the reported blockers first.
7. **Select the existing provider** in the Brain runtime environment:

   ```bash
   export BRAIN_WINDOWS_CLOUD_PROVIDER=opennebula
   export BRAIN_OPENNEBULA_TEMPLATE_ID='<reviewed-template-id>'
   export BRAIN_OPENNEBULA_VM_NAME='alksa-windows-01'
   ```

8. **Review before provisioning**: inspect the executor and provider contract, confirm template, network, storage, quota, and cost/energy impact. Provisioning and destruction remain disabled unless the operator explicitly sets `BRAIN_WINDOWS_CLOUD_ALLOW_APPLY=true`. Do not set that flag until the plan and target have been reviewed.
9. **Verify the guest**: a VM object or OpenNebula state of RUNNING is not proof Windows booted. Require guest-side Windows Server 2025 identity, agent heartbeat, and a fresh challenge/response before marking the cloud VM healthy.
10. **Prove independence**: run deployment and guest verification while Arkan is offline/unregistered. Record OpenNebula host identity and guest heartbeat evidence; simulation or GitHub runner results are not enough.

## Current limits / honest status

- This change adds a host preflight, safety tests, and deployment runbook only.
- It does not install OpenNebula, create a VM, or start Windows Server.
- A cloud VM has not been proven running.
- The existing OpenNebula provider adapter requires a real endpoint, CLI credentials, and a pre-created template.
- If the host has less than 8 GiB RAM, treat it as blocked for this setup; do not claim readiness based on a simulator or GitHub Actions test.
- Arkan is explicitly excluded and cannot be used as a fallback host.
- Prefer a self-hosted host to avoid mandatory paid cloud usage. No paid Azure/AWS resources are created by these steps.

## References

- OpenNebula documentation: https://docs.opennebula.io/
- Electronic Brain OpenNebula provider: `brain_v12/brain/opennebula_windows_cloud_provider.py`
- Provider factory: `brain_v12/brain/windows_cloud_provider_factory.py`
- Windows Cloud Executor and guest verification gate: `brain_v12/brain/windows_cloud_executor.py`
