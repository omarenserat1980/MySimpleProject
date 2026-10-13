# Family Governance for Electronic Brain

This module introduces an explicit family oversight policy for future Brain planning and execution stages. It is a policy evaluator, not an identity provider, messaging system, or complete authorization service.

## Roles

- `FAMILY_GUARDIAN`: intended approval role for high-impact actions, once a trusted identity/consent integration verifies the person.
- `FAMILY_MEMBER`: family participation role; does not by itself authorize high-impact actions.
- `FAMILY_VIEWER`: read-only oversight role.

## Gate behavior

- Low-risk, reversible local actions can pass without family approval.
- High/critical-risk or irreversible actions, plus publishing, external network access, deletion, credential changes, device control, private-data sharing, spending, and paid-resource creation require scoped guardian approval.
- Approval must be explicitly approved, identity-verified by a trusted integration, scoped to the exact action, and carry a consent reference. This module only checks those fields; it does not authenticate the approver.
- Safety denials cannot be overridden by family approval.
- `real_os_boot` always remains behind a separate execution and guest-evidence gate. Family approval alone never proves or enables a Windows boot.

## Integration contract

Call `FamilyGovernance.evaluate(...)` before scheduling or executing actions in future orchestration stages. Until an authenticated consent provider is connected, do not set `identity_verified=True` based only on a user-supplied name or string. Record policy decisions in the project's audit trail when integrated. Do not expose private family information to other members without explicit permission.

## Current boundaries

This PR adds a tested policy component and documentation. It does not yet wire the gate into every existing Brain executor, create family accounts, send notifications, change account-level parental controls, or establish real-world identities/consent. No cloud spending, device access, or external network access is enabled by this change.
