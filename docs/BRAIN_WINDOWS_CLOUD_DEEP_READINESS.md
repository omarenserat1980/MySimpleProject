# Brain Windows Server 2025 Cloud Readiness — Deep Gate

## Objective

A Windows Server 2025 VM is not considered READY merely because Azure/Terraform created it.

Brain must establish four independent proofs:

1. **Provider proof** — Azure resource exists and belongs to the expected provider/subscription/resource group.
2. **Hardware/resource proof** — requested CPU, memory, storage and network resources are allocated and within declared limits.
3. **Guest proof** — Windows Server 2025 booted and the Brain guest agent produced a fresh authenticated heartbeat.
4. **Control-plane proof** — the node is admitted by Mission Control / Execution Kernel with a lease and fencing epoch.

## Provisioning state machine

PLANNED -> REVIEWED -> APPLYING -> PROVISIONED -> GUEST_BOOTING -> GUEST_VERIFIED -> ADMITTED -> READY

Failure states:

BLOCKED, QUARANTINED, DEGRADED, STALE, DESTROY_PENDING

No state transition to READY is allowed from PROVISIONED alone.

## Identity

The cloud VM identity must include:

- provider
- subscription/resource identity
- resource group
- VM resource ID
- node_id
- Brain piece/graph identity
- observation timestamp
- evidence IDs

Secrets/passwords are never written into Brain evidence, logs, outputs, or Git.

## Network security

The current Terraform contract permits WinRM 5986 only from an explicit CIDR. Never use 0.0.0.0/0.

Preferred future control path:

Brain control plane -> private network / Bastion / managed secure channel -> Windows guest agent.

Public WinRM should be treated as transitional management access, not the Brain's long-term control plane.

## Cost gate

Before APPLY, Brain must have an explicit approved plan and a declared VM size/region. Azure Windows infrastructure may incur charges; free-tier/credit eligibility must be verified externally and never assumed.

## Runtime truth

Infrastructure verification and guest-runtime verification remain separate.

READY requires:

- Windows Server 2025
- x86_64/amd64
- provider identity match
- VM identity match
- node state READY/RUNNING
- capabilities: windows-server-2025, windows-cloud, brain-heartbeat
- fresh heartbeat
- valid Brain evidence
- no quarantine/fencing conflict

## Recovery

If the VM exists but heartbeat is stale:

1. mark node STALE
2. stop new missions
3. collect provider status
4. attempt bounded guest recovery
5. re-verify heartbeat
6. otherwise quarantine
7. never silently recreate the whole server if a piece-level repair is possible

## Definition of done

The Windows cloud server is DONE only when Brain can answer, with evidence:

- Which Azure VM?
- Which subscription/resource group?
- Which region?
- Which exact resource shape?
- Which hardware/resource pieces?
- Which network path?
- Which Windows version?
- Which Brain node identity?
- When was it last observed?
- Which heartbeat proves it is alive?
- Which execution lease admits it?
- What happens if one piece fails?

A Terraform apply without these answers is provisioning, not completion.
