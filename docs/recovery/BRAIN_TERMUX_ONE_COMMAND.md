# One-command Electronic Brain on Termux

## Goal
After the repository is already cloned on a Termux device, install a small command surface once and use `brain start`, `brain status`, `brain diagnose`, and `brain logs` instead of repeatedly typing long paths and commands.

## First-time install
From Termux, in the canonical checkout:

```bash
bash ~/MySimpleProject/brain_v12/tools/brain install
```

Then use:

```bash
brain status
brain start
brain diagnose
brain logs
```

The install command creates `$PREFIX/bin/brain` only if the name is free, or updates a shim previously created by this installer. It refuses to overwrite an unrelated command. The shim contains only the local repository path, not credentials.

## Commands
- `brain install`: install the short command.
- `brain start`: call the existing idempotent runtime bootstrap; it does not delete project state or replace keys.
- `brain status`: read-only device/repository/key-file-presence/HTTP health summary.
- `brain diagnose`: status plus tool/log-file presence. It never prints key material or reads the contents of `~/.brain_env`.
- `brain logs`: display the latest runtime logs. Review logs before sharing them; application logs can contain operational details.

## Safety and limitations
- This command is an ergonomic wrapper around the existing runtime; it does not make an unreachable server reachable.
- Redmi model `23129RN51X` may use its own local API. Realme model `RMX3710` must use a reachable, authenticated remote Brain endpoint; `127.0.0.1` on Realme means Realme itself.
- A locally generated key is not proof that the server accepts it. The server's authentication registry/secret configuration must be set up separately, with a different key per device.
- Do not copy the Redmi key to Realme, do not commit secrets, and do not share raw logs containing sensitive data.
- `brain status` proves only the HTTP health endpoint response, not an authenticated agent heartbeat or successful task execution.
- Automatic launch after Android reboot is deliberately not enabled by this installer. That requires Termux:Boot and an explicit user-side setup; Android battery/background restrictions still apply.
- No APK build, destructive cleanup, server restart, cloud deployment, or paid service is triggered by this wrapper.
