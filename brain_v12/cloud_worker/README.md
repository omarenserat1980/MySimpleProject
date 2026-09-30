# Brain Cloud Worker Runtime
Long-running .NET Worker Service for Electronic Brain. Independent periodic workers are coordinated by the Brain Supervisor.
Intervals: supervisor 5s; quality 10s; video/self-healing/health 15s; mining 30s; economic 5m; research 2h; architect 4h.
Safety: no money movement, external publishing, application submission, contracts, or policy changes. Mining only coordinates explicitly registered user-owned workers and never mines in GitHub Actions. Video delegates to the existing film/control-plane implementation. Research and architecture workers observe/propose; repository verification remains required.
Each tick is awaited before the next tick, preventing timer overlap. The runtime is cloud-ready but is NOT claimed live until a user-owned long-running host is connected.
Build: dotnet build brain_v12/cloud_worker/BrainCloudWorker.csproj
Run: dotnet run --project brain_v12/cloud_worker/BrainCloudWorker.csproj