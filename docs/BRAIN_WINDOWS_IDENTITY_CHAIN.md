# Brain Windows Identity Chain

A Windows Cloud node is admitted only after identity binding.

Flow:

Azure VM identity
-> Windows guest attestation
-> enrollment token
-> first identity bind
-> persistent guest identity
-> subsequent heartbeat identity match
-> evidence
-> Fabric eligibility
-> execution lease

Rules:

- Enrollment token authenticates enrollment but does not prove guest identity.
- First valid Windows Server 2025 attestation binds the guest identity to the node.
- Later heartbeats must match the bound identity.
- Identity drift is a hard fail and must quarantine the node.
- A stale or quarantined node cannot receive new jobs.
- This is guest identity attestation, not yet Azure hardware-root attestation.
- Never log raw enrollment tokens, admin passwords, or cloud secrets.

Recovery:

1. mark node QUARANTINED on identity drift;
2. revoke/expire enrollment;
3. stop scheduling;
4. obtain fresh provider + guest evidence;
5. create a new enrollment only after identity is reconciled;
6. re-admit through the Execution Kernel.

This prevents a copied VM image or stolen node identifier from silently becoming the original Brain node.
