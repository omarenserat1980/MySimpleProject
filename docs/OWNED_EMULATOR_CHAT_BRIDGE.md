# Owned-emulator Chat Bridge

## Purpose

This bridge restores a narrow task path between a trusted GitHub issue and the
already-existing Brain simulation API. GitHub is only a task relay; no GitHub
Actions runner is used to execute the task. The local bridge polls the issue,
calls Brain on loopback, records local evidence, and posts a sanitized result.

The first supported task is intentionally fixed:

- Issue title: [BRAIN-EMU] STATUS
- Entire issue body: task=status
- Allowed API call: GET http://127.0.0.1:8012/api/remote-fabric/status
- No arbitrary commands, shell, remote host, physical device, SSH, ADB, or public listener.

## Prerequisites

- The Brain API must already be running in the same local environment on port 8012.
- GitHub CLI (gh) must be installed and authenticated as an account allowed to
  read issues and comment/close the task issue.
- Configure the exact GitHub login(s) trusted to issue this read-only task.
- The bridge fails closed when the allowlist is empty or the API is not explicitly
  reporting mode=VIRTUAL and reality=SIMULATED.

## Run once

From the repository root, in the same environment as the Brain API:

Linux / Termux / macOS shell:

    export BRAIN_BRIDGE_ALLOWED_GITHUB_LOGINS="omarenserat1980"
    python -m brain_v12.brain.owned_emulator_chat_bridge --once

PowerShell:

    $env:BRAIN_BRIDGE_ALLOWED_GITHUB_LOGINS = "omarenserat1980"
    python -m brain_v12.brain.owned_emulator_chat_bridge --once

To keep polling, omit --once. The default poll interval is 15 seconds; the
minimum allowed interval is 5 seconds. Stop the process with Ctrl+C.

The bridge uses the existing gh CLI login; it does not ask for or print a token.
Do not place a token or BRAIN_CONTROL_KEY in an issue, command line, source file,
or conversation. The status route is read-only and does not require the control key.

## Submit the task

Create a GitHub issue in omarenserat1980/MySimpleProject with the exact title
[BRAIN-EMU] STATUS and exact body:

    task=status

The author must match BRAIN_BRIDGE_ALLOWED_GITHUB_LOGINS. Any other title, body,
or author is ignored. After one attempt the bridge writes local evidence under
.brain/owned_emulator_bridge/evidence/, comments the sanitized result, and closes
the issue. A processed-issue ledger prevents duplicate probes after restart.

## Evidence and interpretation

Each local evidence JSON includes a SHA-256 digest, issue number, timestamp,
HTTP status, and a small allowlist of returned fields. The digest detects
accidental changes; it is not a remote signature or proof against a compromised
local host.

- ok=true and verified_simulation=true means the API explicitly reported VIRTUAL
  and SIMULATED and returned ok=true.
- CONNECTION_ERROR or TIMEOUT means the local API was not reachable by the bridge.
- SIMULATION_NOT_VERIFIED means an HTTP response arrived but did not prove the
  expected simulation state.
- A GitHub issue being processed is not itself evidence of a successful API check.

## Boundaries

This is a relay for one read-only simulation-status probe, not a general remote
executor. Do not extend it to arbitrary shell commands. Any future task type must
have a fixed schema, explicit author authorization, a constrained target, an
independent verification rule, and tests before it is enabled.
