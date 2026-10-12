# Brain Authority Model

## Invariant

**Capability does not imply authority.**

The reasoning model can propose. Policy decides. Authorization grants a bounded action. An executor performs only the authorized action. Verification is independent.

## Closed loop

`IDENTITY -> GENERATION -> LEADERSHIP -> POLICY -> AUTHORIZATION -> CAPABILITY -> EXECUTION -> EVIDENCE -> VERIFICATION -> MEMORY`

## Rules

1. Models/reasoners are proposal-only.
2. Executors never grant themselves authority.
3. HIGH and CRITICAL actions require explicit human approval in the current policy implementation.
4. Missing/ambiguous risk, capability, or authority fails closed.
5. Root authority is explicit and auditable; it is not inferred from a model, workflow, runner, or executor label.
6. Evidence does not grant execution authority.
7. A newer capability version must not silently widen authority.
8. Windows Server 2025 real boot remains blocked until both cloud execution capability and an authorized, current execution contract exist.
9. Every consequential execution should carry identity, generation, fencing token, task/attempt identity and policy version.
10. Future multi-VM Active/Active requires shared consensus-capable authority; the current SQLite leadership store is not sufficient.

## Security boundary

`MODEL != AUTHORITY`
`WORKFLOW != AUTHORITY`
`EXECUTOR != AUTHORITY`
`EVIDENCE != AUTHORITY`

Authority comes from the policy/control plane and, where required, explicit human approval.
