# Electronic Brain integration diagnostics

Run from the repository root on Python 3.10+:

```sh
python brain_v12/tools/brain_integration_diagnostics.py
```

This runs deterministic software-only XOR checks. It does not claim ASIC hardware
execution, Render availability, MCP reachability, or OAuth compliance.

For an explicit read-only probe against a deployed Brain service:

```sh
python brain_v12/tools/brain_integration_diagnostics.py --base-url https://YOUR-BRAIN-HOST
```

The live probe attempts `GET /mcp`, then JSON-RPC `initialize`,
`tools/list`, and the read-only `tools/call` for `brain.status`. It reports
HTTP status and a redacted response summary. It does not print arbitrary tool
output or authorization headers. If the endpoint requires a bearer token, set
`BRAIN_DIAGNOSTICS_BEARER_TOKEN` in the process environment; do not put the
token in command-line arguments or commit it to source control.

The tool separately probes standard OAuth metadata locations. Metadata discovery
is not proof of OAuth 2.1 authorization-code flow or PKCE. This script does not
perform login, create sessions, mutate service configuration, trigger deployment,
or prove that the deployed service is running this repository revision.

## Result interpretation

- `local_asic.status=PASS`: all four XOR truth-table cases passed in software.
- `live_mcp.status=PASS`: the HTTP MCP checks and read-only `brain.status`
  call returned the expected JSON-RPC envelope.
- `FAIL`: a check was executed and did not meet its expected result.
- Network errors or HTTP 401/403/404 are evidence of a blocked/unavailable
  endpoint, not evidence that local tests failed. Preserve each step's status
  and investigate route, auth, deployment identity, and service logs separately.

Use the report as diagnostic evidence only. Final integration acceptance still
requires confirming the actual Render service/commit, a real OAuth 2.1 + PKCE
flow where required, and the expected MCP tool-call response from that service.
