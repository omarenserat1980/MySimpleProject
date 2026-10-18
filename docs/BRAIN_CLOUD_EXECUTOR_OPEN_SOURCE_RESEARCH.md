# Brain Cloud Executor MAX — Open-Source Research

**Reviewed:** 2026-10-13  
**Purpose:** Identify reusable patterns and projects; do not add dependencies merely because they are popular.

## Candidate projects and fit

| Project | Relevant capability | Fit for Brain | Decision |
|---|---|---|---|
| [SPIFFE](https://github.com/spiffe/spiffe) / [SPIRE](https://github.com/spiffe/spire) | Workload identity, node/workload attestation, short-lived identities, trust bundles | Strong architectural reference for trusted executor identity across heterogeneous hosts. It is not a drop-in replacement for Brain's current enrollment flow and would require operating a SPIRE server/agent and platform-specific attestors. | Study and prototype behind a provider/identity adapter only after current authentication is repaired. |
| [OpenTofu](https://github.com/opentofu/opentofu) | Infrastructure-as-code planning and controlled apply | Relevant to provisioning adapters; its plan/apply separation matches Brain's explicit approval gate. It does not itself supply free compute or guarantee provider availability. | Use as an optional provider adapter where existing Terraform-compatible modules work; require plan review and explicit approval before apply. |
| [Nomad](https://github.com/hashicorp/nomad) | Workload scheduling and orchestration | Useful reference for placement, job lifecycle, retries, and resource constraints, but introduces a scheduler control plane and operational requirements. | Study patterns first; do not replace the existing Brain scheduler until comparative tests justify migration. |
| [Incus](https://github.com/lxc/incus) | Linux containers and virtual-machine lifecycle | Potential self-hosted executor substrate on supported Linux hosts. Not a solution for running KVM inside a hosted service that does not expose virtualization capabilities. | Optional local/self-hosted adapter; capability-detect before use. |
| [HashiCorp Vault](https://github.com/hashicorp/vault) | Secret storage, dynamic credentials, key lifecycle | Potential centralized secrets provider but adds operational complexity. | Keep current protected secret-store integration; define a secret-provider interface so Vault can be added if justified. |

## Primary-source references

- SPIRE concepts and attestation: https://spiffe.io/docs/latest/spire-about/spire-concepts/
- SPIRE configuration and node/workload attestors: https://spiffe.io/docs/latest/deploying/configuring/
- OpenTofu workflow and plan/apply: https://opentofu.org/docs/v1.7/intro/
- OpenTofu project and licensing information: https://github.com/opentofu/opentofu
- SPIRE project and licensing information: https://github.com/spiffe/spire
- Nomad source: https://github.com/hashicorp/nomad
- Incus source: https://github.com/lxc/incus
- Vault source: https://github.com/hashicorp/vault

## Integration principles

1. Prefer standards, stable APIs, and adapters over forking a large external project.
2. Review current maintenance, release cadence, security advisories, transitive dependencies, and the exact license before introducing code.
3. Do not claim a project is free to operate merely because its source is open. Hosting, storage, support, and compute may still cost money.
4. Do not deploy SPIRE, Vault, Nomad, or Incus to production as part of this research-only change.
5. Keep Brain's existing fail-closed attestation until a separately reviewed migration has equivalent or stronger tests.
6. Test actual host support. Termux/Android, Render-hosted services, Linux self-hosted runners, and Windows hosts have different isolation and virtualization capabilities.

## Recommended engineering sequence

1. Establish a fresh successful Brain challenge/issue/verify/consume flow with the existing design.
2. Add integration tests for concurrent challenge/attestation consumption and configuration failures.
3. Formalize an executor identity interface and a provider capability contract.
4. Prototype SPIFFE/SPIRE only in an isolated test environment; compare operational cost and security properties to the current design.
5. Add OpenTofu as an optional plan-only provider adapter, and test that apply cannot run without an explicit authorization.
6. Evaluate Nomad or Incus only when Brain's own scheduler or self-hosted capacity needs justify the extra service.
