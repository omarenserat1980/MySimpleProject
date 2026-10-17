# Windows cloud preflight

This directory contains a guarded preflight for running the canonical Electronic Brain repository on a Windows Server 2025 cloud VM.

1. Provision a licensed Windows Server 2025 VM through the chosen cloud provider first.
2. Clone/check out the intended repository revision using an approved authentication method.
3. Open PowerShell and run:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\deploy\windows-cloud\Preflight-BrainCloud.ps1 -RepoPath C:\ElectronicBrain
```

The script installs Python dependencies into a repository-local virtual environment, checks that the application imports, and checks the local readiness endpoint. It **does not** create cloud resources, open firewall ports, configure RDP, install a persistent service, or claim the system has launched. Review the dependency layout and provider security policies before use.
