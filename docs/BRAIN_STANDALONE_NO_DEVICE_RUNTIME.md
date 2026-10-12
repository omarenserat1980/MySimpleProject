# Electronic Brain — Standalone Runtime Without Devices

## Objective

Run the Brain API without Arkan/Windows/Hyper-V, Redmi, Realme, device agents,
hardware discovery, emulators, or a GitHub fetch during startup.

## Entry point

Run `bash brain_v12/tools/brain_standalone_launcher.sh` from any working
directory. The script resolves the repository root, selects Python, sets the
persistent runtime home (default `~/.brain/runtime`), and directly starts
`brain_v12.mcp_server:app` with Uvicorn.

- Default bind: `127.0.0.1:8012` (local-only by default).
- Override the bind address with `BRAIN_HOST`; override the port with `PORT`.
- Override persistent state with `BRAIN_RUNTIME_HOME`.
- No device ID, device key, Termux agent, emulator, Windows VM, or GitHub
  source synchronization is required by this launcher.
- GitHub Actions is verification only, not the runtime authority.

## Important verification boundary

This launcher establishes a separate no-device startup path; it does not by
itself prove that every Brain capability is available offline or that the
complete application has no transitive optional integration dependency.
Capabilities that genuinely require external services (for example model APIs,
publishing, or remote cloud execution) may remain unavailable while the core
API and local-state functions run. Those integrations must fail as optional
capabilities rather than prevent core startup.

## Acceptance checks

Run the contract test:

```sh
python -m unittest brain_v12.tests.test_standalone_launcher -v
```

Then launch the API and verify `/health` and `/api/system/readiness` on the
selected host/port. A source-contract test is not a substitute for that live
runtime verification.
