# Brain Git

Brain Git is the Brain-owned Git service boundary. GitHub remains an external mirror/backup and integration surface, not the Brain's internal repository authority.

## Architecture

- Gitea provides the Git repository engine and web/API surface.
- Brain Git policy owns repository identity, authorization, audit requirements, and mirror policy.
- Persistent data lives outside the application container.
- External GitHub synchronization is explicit and authorization-gated.
- No credentials are stored in this repository.

## Initial deployment

The compose stack starts Brain Git on the private Brain Cloud network. Do not expose it publicly until authentication, TLS, backups, and an owner/admin account have been configured.

## Authority rule

`BRAIN_GIT_PRIMARY` means new internal changes are authored in Brain Git first. `GITHUB_MIRROR` is an external mirror/backup. Production changes still require CI verification and the existing authorization gate for sensitive external actions.
