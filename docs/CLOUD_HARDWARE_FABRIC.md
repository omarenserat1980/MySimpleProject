# Electronic Brain Cloud Hardware Fabric

## Purpose

The Cloud Hardware Fabric describes virtual hardware that Brain can request from a cloud provider instead of relying on the limited RAM/CPU of the local Arkan laptop. It models CPU, RAM, storage, networking, and optional GPU capacity behind one provider-neutral interface.

## Important distinction

- **Cloud VM / compute** supplies real remote CPU and RAM. This is the option that can remove local-memory pressure for Windows Server 2025 or Brain workloads.
- **Cloud storage** can hold backups and artifacts, but does not act as RAM or CPU.
- **Cloud networking** connects Brain agents and remote VMs.
- **GPU capacity** is a separate, often costly SKU and must be requested explicitly.
- **Azure Arc** manages/inventories existing physical or non-Azure servers; it does not add RAM or CPU to the laptop. See [Azure Arc overview](https://learn.microsoft.com/en-us/azure/azure-arc/servers/overview).
- Remote cloud compute is not the same as passing a physical USB/GPU device through to a VM.

## Implemented foundation

`brain_v12/brain/cloud_hardware_fabric.py` provides:
- a hardware request schema for CPU, RAM, disk, network, and GPU;
- provider capacity offers;
- a fail-closed cost/eligibility gate;
- a capacity planner that never provisions resources.

The planner returns `PLAN_READY_NOT_PROVISIONED` when an eligible offer fits. This is only a plan, not proof that the region has live capacity or that deployment succeeded.

## Safety rules

1. Do not create, resize, or start billable cloud resources from planning code.
2. Keep paid provisioning disabled unless the user explicitly approves a documented cost ceiling.
3. Do not label a resource free until account-specific eligibility, SKU, region, OS image, storage, IP/network, and remaining allowance are checked. Azure VM compute, disks, IPs, licensing, and networking can have separate costs; see [Azure VM overview and billing](https://learn.microsoft.com/en-us/azure/virtual-machines/overview).
4. Azure's free VM allowance is account- and SKU-limited; the public free-account description is not proof that this user's subscription is eligible. See [Azure free account services](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/cost-management-billing/manage/create-free-services.md).
5. A deployment adapter must separately implement dry-run, cost estimate, explicit approval, idempotent apply, teardown, heartbeat verification, and evidence capture.
6. Never use cloud resources as an excuse to delete or overwrite the existing local VHDX/checkpoints.

## Next integration steps

1. Read-only Azure subscription/benefit/SKU/region checks.
2. Produce a capacity and cost report without applying Terraform.
3. Only after entitlement and cost are proven, implement a separate Azure adapter and require an explicit approval token before deployment.
4. Enroll the cloud VM into Brain, verify a fresh heartbeat, and prove Windows boot/accessibility.
