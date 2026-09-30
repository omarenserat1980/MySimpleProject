# Brain Cloud Worker Runtime

Long-running provider-neutral .NET Worker Service for Electronic Brain. Independent periodic workers are coordinated by the Brain Supervisor.

## Runtime guarantees
- Nine bounded BackgroundService workers use PeriodicTimer; each tick is awaited before the next tick.
- Durable heartbeat is written atomically.
- Worker registration is persisted in `/var/lib/brain/workers.json` by default.
- Jobs use exclusive leases with renewal/release and expiry, preventing duplicate active ownership.
- No external side effect is performed by the runtime by default; sensitive actions remain behind AuthorizationGate.
- The runtime does not require Oracle Cloud, Google Cloud, Render, or paid media APIs.

## Intervals
Supervisor 5s; quality 10s; video/self-healing/health 15s; mining 30s; economic 5m; research 2h; architect 4h.

## Self-test
`dotnet run --project brain_v12/cloud_worker/BrainCloudWorker.csproj -- --self-test`

The self-test verifies registration, heartbeat, duplicate-lease rejection, renewal, and release.

## Hosting
A real 24/7 worker requires a user-owned machine/host that stays online. GitHub-hosted runners are short-lived; self-hosted runners can provide persistent user-managed execution when configured and kept online.
