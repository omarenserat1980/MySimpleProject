# Brain Defense-in-Depth

This layer complements the existing SecurityGuard and SecurityHardening
primitives.

## API boundary
- Do not trust arbitrary forwarded headers for identity.
- Hash operational client identifiers before evidence/logging.
- Apply restrictive response headers.
- Keep control authentication fail-closed.
- Rate-limit before expensive work.

## Execution boundary
- Treat code execution as high risk.
- Keep workspace allowlists narrow.
- Never pass secrets as command-line arguments.
- Never execute untrusted user input as a shell command.
- Record execution evidence without command secrets.

## Supply-chain boundary
- CI permissions default to read-only.
- Review third-party Actions before adoption.
- Pin critical Actions/dependencies when practical.
- Scan source and workflow files for credential material.
- Do not weaken security tests to make CI green.

## Recovery boundary
- Preserve evidence before repair.
- Rotate/revoke compromised credentials.
- Restore only from verified backups.
- Re-run security and regression gates after recovery.

## Autonomy boundary
Brain may autonomously repair its software, but a repair that changes the
security boundary cannot self-authorize the new privilege. Such a change must
remain behind a protected deployment/authorization path.

## Current status
These are defensive controls, not a claim of immunity from compromise.
Independent verification remains required.
