# ChatGPT Suggestion → Brain Execution

## Goal
Turn ChatGPT suggestions into structured Brain proposals and execute them only through explicitly registered Brain-owned tools.

## Lifecycle
1. Propose a named action, rationale, arguments, and risk level.
2. Reject any tool not present in the trusted registry.
3. Use dry-run by default.
4. Require approval for high/critical risk and a mutation gate for medium/high/critical changes.
5. Record execution outcomes and require verifiable evidence before marking the action complete.

## Safety boundaries
This component does not run arbitrary ChatGPT-generated code, shell commands, native PowerShell, or unrestricted remote commands. Register only narrow, trusted Brain APIs and emulator operations. Keep physical-host operations separate and explicitly authorized. A simulated Arkan result is never proof that a real host or Windows Server VM booted.
