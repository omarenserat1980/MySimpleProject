# Brain Git Security Baseline

1. Keep the service private until an owner account exists.
2. Never commit administrator passwords, OAuth secrets, SSH private keys, or GitHub tokens.
3. Require authentication for repository access.
4. Keep external mirroring disabled by default.
5. Treat mirror pushes, public publishing, repository deletion, and access-policy changes as sensitive actions.
6. Back up the persistent volumes before upgrades.
7. Verify commits through Brain CI before treating them as production changes.
8. Record administrative and synchronization actions in Brain Audit.
