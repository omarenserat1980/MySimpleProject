# Brain Windows Cloud Progress Gate

This read-only command consolidates the four live Windows Cloud readiness endpoints into one report and names the next actionable blocker. It exists to prevent repeated manual checks of the same state.

## Run from any directory

After pulling `main`, run the script by its path (the script locates the checkout from its own file path):

```bash
python ~/MySimpleProject/brain_v12/tools/windows_cloud_progress_gate.py
```

Use another API base URL when the API is not local:

```bash
python ~/MySimpleProject/brain_v12/tools/windows_cloud_progress_gate.py --base-url http://127.0.0.1:8012
python ~/MySimpleProject/brain_v12/tools/windows_cloud_progress_gate.py --json
```

Exit code `0` means the report found no current readiness blockers other than the always-open real-boot evidence obligation. Exit code `2` means actionable blockers remain. The report does not infer successful Windows boot from HTTP 200.

## What it checks

- `/api/brain/windows/cloud/readiness`
- `/api/brain/windows/cloud/secrets/readiness`
- `/api/brain/windows/cloud/status`
- `/api/brain/windows/status`

It prints HTTP reachability and sanitized status/missing-field names only. It never prints environment values or secret contents.

## Safety and limits

- Read-only; no Git mutation, secret creation, node enrollment, VM provisioning, or cloud apply.
- Does not claim `BRAIN_RUNNER_WATCH_TOKEN` exists; confirm that through the GitHub watcher workflow.
- Presence-only enrollment readiness is not proof of valid credentials.
- Provider readiness is not proof a VM exists.
- VM existence or heartbeat is not proof Windows booted from its installed disk.
- Real boot must be proven by trusted evidence and the Golden Loop Closure Auditor.
- Review provider cost and an explicit plan before any infrastructure apply. No paid cloud resources are created by this tool.
