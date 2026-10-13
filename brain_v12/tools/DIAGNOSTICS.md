# Brain-native diagnostics (software-only)

These tools are diagnostic helpers. They do not deploy, merge, modify Render settings,
or change secrets.

## 1. ASIC simulator smoke test (local)

From the repository root:

```bash
python brain_v12/tools/asic_simulator_smoke.py
```

The report checks the XOR truth table and cycle-limit enforcement. A passing result
proves only that the local software simulator behaved as expected. It is not a live
Render/MCP result and is not a physical ASIC measurement.

## 2. Live MCP endpoint probe

```bash
python brain_v12/tools/mcp_live_probe.py --url https://YOUR-HOST/mcp
```

The probe performs GET, `initialize`, `tools/list`, and (by default) calls the
advertised read-only `brain.status` tool. It reports HTTP status and protocol-level
success without printing response payloads from the tool call.

If the MCP endpoint requires a bearer token, set it in the environment before running
the probe; the token value is never printed:

```bash
export BRAIN_MCP_BEARER_TOKEN='...'
python brain_v12/tools/mcp_live_probe.py --url https://YOUR-HOST/mcp
```

Do not place tokens in command-line arguments, source code, issue comments, or logs.
This optional bearer-token mechanism is not an OAuth 2.1/PKCE test. A successful probe
does not certify OAuth/PKCE, deployment identity, or the full Brain/ASIC integration.
Use only an explicitly approved, known MCP endpoint. The script does not discover or
guess a production URL.

## Evidence boundaries

- **Local simulator pass:** software behavior for the vectors tested.
- **Live MCP pass:** the selected URL responded to the observed HTTP/JSON-RPC sequence.
- **OAuth/PKCE acceptance:** requires a separate, specifically designed auth-flow test
  against the real endpoint without exposing tokens.
- **Production acceptance:** requires matching deployment identity and runtime evidence;
  GitHub Actions alone is insufficient.
