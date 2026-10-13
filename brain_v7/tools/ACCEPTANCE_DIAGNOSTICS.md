# Brain V7 acceptance diagnostics

This tooling belongs to the **new Brain V7 project** under `brain_v7/tools`.
It does not use the legacy `brain_v12` paths and does not deploy or change secrets.

## Software ASIC reference tests

From the repository root or from the Brain V7 environment:

```sh
python brain_v7/tools/brain_v7_acceptance_diagnostics.py --output brain_v7/asic-acceptance-report.json
```

The default run checks XOR, half-adder and full-adder identities, plus seeded
property-style cases. A PASS proves only the software reference model. It is
not evidence of physical ASIC/silicon or FPGA execution.

## Live V7 health and MCP

First inspect the V7 source and deployment configuration to find the exact
health URL and MCP POST endpoint. Do not assume that the relay root or `/mcp`
is the correct MCP endpoint.

```sh
python brain_v7/tools/brain_v7_acceptance_diagnostics.py \
  --health-url 'https://EXACT-V7-HOST/health' \
  --mcp-url 'https://EXACT-MCP-HOST/EXACT-PATH' \
  --output brain_v7/integration-acceptance-report.json
```

If authentication is required, export `BRAIN_V7_MCP_BEARER_TOKEN` in the
runtime environment; do not put tokens in command arguments or report files.
For tool calls, set `BRAIN_V7_MCP_TEST_TOOL` only to a safe tool name returned
by `tools/list`. The tool emits status and response keys, not arbitrary MCP
response content.

## OAuth 2.1 + PKCE and cloud worker

These are deliberately separate acceptance gates. Metadata discovery and
local tests do not prove the authorization-code flow. End-to-end acceptance
requires a configured test client, registered redirect URI, S256 challenge,
matching verifier at token exchange, protected-resource access with the issued
token, and negative tests for a wrong verifier and unauthenticated access.
Never store access tokens, authorization codes, verifiers, or private keys in
reports or CI artifacts.

Cloud-worker acceptance requires an actual authorized job, bounded execution,
and evidence tying the result to the job ID and source commit. The Brain
supervisor remains the approval authority; workers may not authorize their own
deployments.

## Release rule

Keep each gate independent: software ASIC, live V7 health, MCP initialize /
initialized notification / tools/list / tools/call, OAuth 2.1 + PKCE, and
cloud-worker provenance. Report `PASS`, `FAIL`, `BLOCKED`, or `NOT_PROVEN`
honestly. No Render deployment or secret change is performed by this tool.
