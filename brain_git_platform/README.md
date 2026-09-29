# Brain Git Platform

Brain Git Platform is the internal source-control and automation plane for Brain Cloud.

## Boundary

The platform is designed so Brain runtime operations do not depend on GitHub.com:

- Git repositories are stored under the configured Brain Git root.
- Git operations use the local Git executable/library boundary.
- CI jobs execute on Brain-owned runners.
- Artifacts, logs, workflow state, and audit events remain in Brain storage.
- GitHub integration is an optional import/export bridge, not a runtime dependency.

## Services

- `api/` — repository, branch, commit, pull-request, workflow and artifact API.
- `storage/` — repository and object storage boundary.
- `runner/` — Brain CI runner contract.
- `auth/` — users, teams, roles and scoped tokens.
- `audit/` — immutable operational audit events.
- `bridge/` — optional GitHub synchronization/import/export.

## Isolation rule

Production Brain workflows must call the Brain Git Platform API or its local Git service. They must not call GitHub APIs directly.

The migration is additive first: existing GitHub Actions remain available as an external bridge while Brain-native workflows are introduced and verified.
