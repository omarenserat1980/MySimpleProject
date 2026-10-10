# Electronic Brain — One-line Cross-Platform Activation

The goal is one short command, not a pasted script. The bootstrap is intended for the supported shell on each platform:

- **Termux / Android, Linux, macOS (Bash):**
  ```bash
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main/brain_v12/tools/brain-one.sh)" -- activate
  ```
- **Windows PowerShell:** (runs the Linux runtime inside WSL; native Windows is not falsely reported as the Linux runtime)
  ```powershell
  irm https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main/brain_v12/tools/brain-one.ps1 | iex
  ```

After installation, use `brain status`, `brain diagnose`, or `brain start` where the installed command is on PATH.

## Safety contract

- Uses `$HOME/MySimpleProject` when it is already a Git checkout.
- Clones `main` only when that path does not exist. It never resets, cleans, checks out another branch, or overwrites a non-Git directory.
- If a pre-existing checkout lacks runtime files, it stops and asks for review rather than replacing it.
- Installs the command shim only if the command name is unused or the existing shim is already marked as owned by Electronic Brain.
- Does not print key values, invent device IDs, copy keys between devices, fabricate heartbeats, or bypass server authentication.
- Different Android models can use the same Bash entrypoint. The existing runtime launcher remains responsible for model-to-agent mapping and rejects unknown or mismatched identities.
- Windows requires WSL for the Linux runtime. The PowerShell entrypoint reports a clear error if WSL is absent.
- One-line activation is not proof of full health. It reports local API HTTP status; verify the worker heartbeat and deployment convergence separately.

## Device prerequisites

- Termux: Git, curl, Bash, and Python dependencies needed by the project runtime.
- Linux/macOS: Git, curl, Bash, Python dependencies, and a usable endpoint/configuration for the selected agent.
- Windows: WSL with a Linux distribution, Git/curl, and the project's runtime dependencies inside WSL.
- Remote devices (for example Realme) must have their own unique `V12_AGENT_ID`, model confirmation if required, a reachable Brain endpoint, and a key registered by the server operator. The bootstrap deliberately does not make up these trust relationships.

## Rollback / recovery

The bootstrap is additive. It does not mutate an existing working tree. The user-owned launcher lives at `~/.local/share/brain/brain-one.sh`; the shim is installed in Termux `$PREFIX/bin/brain` or Unix `~/.local/bin/brain`. Remove only these known installer-owned files if rollback is needed, and preserve project state, databases, keys, and recovery artifacts.
