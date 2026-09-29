# Brain Git Platform

Brain Git Platform is the internal source-control and automation plane for Brain Cloud.

## Runtime boundary

Brain runtime operations are designed to operate without GitHub.com:

- Git repositories are stored under the configured Brain Git root.
- Git operations use the local Brain Git service boundary.
- Native CI jobs execute on Brain-owned runners.
- Workflow state, logs, artifacts, and audit events remain in Brain storage.
- GitHub is an optional import/export bridge only.

## Native execution

The platform now has:

- repository and branch primitives
- native Git Smart HTTP transport for clone/fetch/push
- pull requests and fast-forward merge
- scoped API authentication
- workflow manifests
- durable queued workflow runs
- worker ownership and heartbeat recovery
- runner checkout from Brain Git
- workflow execution
- run logs
- run artifacts
- audit events
- runtime GitHub-isolation verification

The first native workflow is `brain-git-platform-foundation`.

## Authentication

The HTTP runtime requires a Brain-owned bearer token for every endpoint except health:

- `BRAIN_GIT_TOKEN` — secret bearer token
- `BRAIN_GIT_TOKEN_SCOPES` — comma-separated scopes, defaulting to `repo:read,repo:write,workflow:read,workflow:write,pull:write`
- `BRAIN_GIT_MAX_REQUEST_BYTES` — maximum HTTP request body size, default 64 MiB

Example Git remote:

`http://brain-git-host:8090/git/brain/MySimpleProject.git`

The deployment layer must inject the token securely; it must never be committed to the repository.

## Isolation rule

Production Brain workflows must call the Brain Git Platform API or local Git service. They must not require GitHub APIs, GitHub Actions runners, or `GITHUB_TOKEN` at runtime.

GitHub Actions remain an external validation/bridge mechanism during migration. They are not the target execution plane.

## Migration target

`Brain Cloud → Brain Git → Native Scheduler → Brain Runner → Verification → Artifacts/Audit → Production`

The final detach phase removes GitHub credentials and direct GitHub runtime calls from Brain production configuration after the native isolation suite passes.