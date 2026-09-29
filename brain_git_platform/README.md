# Brain Git Platform

Brain Git Platform is the internal source-control and automation plane for Brain Cloud.

## Runtime boundary

Brain runtime operations are designed to operate without GitHub.com:

- Git repositories are stored under the configured Brain Git root.
- Git operations use the local Git service boundary.
- Native CI jobs execute on Brain-owned runners.
- Workflow state, logs, artifacts, and audit events remain in Brain storage.
- GitHub is an optional import/export bridge only.

## Native execution

The platform now has:

- repository and branch primitives
- pull requests and fast-forward merge
- scoped authentication foundation
- workflow manifests
- queued workflow runs
- runner checkout from Brain Git
- workflow execution
- run logs
- run artifacts
- audit events
- runtime GitHub-isolation verification

The first native workflow is `brain-git-platform-foundation`.

## Isolation rule

Production Brain workflows must call the Brain Git Platform API or local Git service. They must not require GitHub APIs, GitHub Actions runners, or `GITHUB_TOKEN` at runtime.

GitHub Actions remain an external validation/bridge mechanism during migration. They are not the target execution plane.

## Migration target

`Brain Cloud → Brain Git → Native Scheduler → Brain Runner → Verification → Artifacts/Audit → Production`

The final detach phase removes GitHub credentials and direct GitHub runtime calls from Brain production configuration after the native isolation suite passes.
