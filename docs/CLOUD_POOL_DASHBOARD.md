# Electronic Brain Cloud Pool Dashboard

The device-backed resource pool browser interface lives at `/cloud-pool.html`.

## Run the Windows bootstrap

From this checkout, start `tools/Run-CloudPool-Setup.cmd`, or run `tools/Start-ElectronicBrain-CloudPool.ps1` in PowerShell. The launcher uses the default checkout path `C:\\Brain\\extract\\MySimpleProject-brain-software-cloud-pool`, creates a local `.venv`, and checks port 8013 without stopping an existing process. It saves status evidence and logs to `C:\\Brain\\logs`. You can override the project path or test port when running the PowerShell script.

## Open it locally

Start `brain_v12.app:app` from this checkout and open:

- `http://127.0.0.1:8013/cloud-pool.html` — resource dashboard
- `http://127.0.0.1:8013/docs` — FastAPI OpenAPI docs

The root UI also has a **موارد Brain** navigation link to the dashboard.

## What the dashboard reads

- `GET /api/cloud-pool/status`: observed host and enrolled-device nodes.
- `POST /api/cloud-pool/plan`: plans resource placement; it does not execute a workload.
- `GET /api/hardware/resources`: measured host capacity, process-local logical leases, and test jobs.
- `POST /api/hardware/plan`: previews a bounded logical capacity plan.
- `POST /api/hardware/allocate`: creates an in-process logical lease and optionally runs the fixed bounded SHA-256 self-test. Requires `X-BRAIN-CONTROL-KEY`.
- `POST /api/hardware/jobs`: runs the fixed bounded SHA-256 self-test on an active lease. Requires `X-BRAIN-CONTROL-KEY`.
- `POST /api/hardware/release`: releases an in-process logical lease. Requires `X-BRAIN-CONTROL-KEY`.

## Important resource semantics

The host node is measured from the machine running the API. CPU count, physical memory, and free disk are measurements, not invented cloud capacity. Enrolled Android/Windows/Linux nodes only appear as healthy/online when their bridge/heartbeat data supports that state.

Software-hardware leases are **logical quotas only**. They are not OS-enforced CPU/RAM reservations, do not create additional physical resources, do not provision external cloud, and are stored in the server process memory (not durable across restart). The built-in probe uses a fixed, bounded SHA-256 workload; it is not arbitrary command execution.

An HTTP 200/API route check proves only that this API instance answers. Actual ASUS node measurements require running the API on ASUS; remote Android or other device execution requires separate enrollment/heartbeat and execution evidence.

## Local validation sequence

1. Run `Run-CloudPool-Setup.cmd` from the bootstrap bundle, or use `Start-ElectronicBrain-CloudPool.ps1` with the existing checkout path.
2. Confirm the script passes its OpenAPI route check and `GET /api/cloud-pool/status`.
3. Confirm `GET /api/hardware/status` reports `capacity.observed: true` for the actual host process.
4. Open `/cloud-pool.html` and verify live values match API responses.
5. Treat remote-node status and test-job evidence as separate checks. Do not infer either from CI success alone.
