# Brain Runtime Cutover

Status: the repository's canonical Brain core is `brain_v12`. The old Brain 6 / Brain V7 factory path is retired as an execution route.

## Enforced changes

- `scripts/brain6_168h.sh` exits with code 78 and never launches the legacy factory worker.
- `scripts/install_brain6_168h.sh` disables/stops the legacy user systemd service, removes its installed unit file, reloads systemd, and does not start any replacement workload.
- `deploy/brain6-168h.service` is inert and has no restart loop.
- `production/BRAIN6_168H.json` is marked `enabled: false` and `retired: true`.
- The C++ and C# Brain 6 supervisors fail closed unless the campaign is explicitly enabled and not retired.
- The supported core entrypoint documented here is `python3 -m brain_v12.app`.

## Preserved intentionally

Historical source, tests, and legacy requirements remain in the repository for traceability. Their presence is not authorization to run them. This change does not delete recovery artifacts, alter Render settings/secrets, change authentication policy, or claim the V12 runtime has been deployed or booted.

## Host-side completion

A repository change cannot modify a systemd unit already installed on a phone or host. After this change is reviewed and merged, run:

```bash
bash scripts/install_brain6_168h.sh
```

on each host where the old user service may have been installed. Then check:

```bash
systemctl --user is-enabled brain6-168h.service
systemctl --user is-active brain6-168h.service
```

The expected service state is disabled/inactive (the first command may report that the unit is not found because the retirement script removes it). Start the canonical Brain only after its own configuration, readiness, and authentication checks pass.
