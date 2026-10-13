# ASIC software model and integration acceptance

## Run the software ASIC model

From the repository root:

```sh
python3 brain_v12/tools/brain_asic_reference_simulator.py --output artifacts/asic-reference-report.json
```

The report includes a PASS/FAIL result, check count, deterministic seed, runtime,
and SHA-256 digest. The model exercises XOR, half-adder and full-adder logic,
including seeded property-style cases. It is explicitly a software reference
model: `physical_hardware_tested=false`. A passing report must never be
described as physical ASIC/silicon validation.

## Live MCP acceptance

Use the existing `brain_integration_diagnostics.py` only after identifying the
actual deployed MCP endpoint from the checked-out source and deployment config.
Do not assume `/mcp` or any host is correct without that evidence. Keep tokens
in the environment (never command-line arguments or reports).

Acceptance evidence must record, separately:
- HTTP status and JSON-RPC response ID for `initialize`;
- successful `notifications/initialized`;
- `tools/list` result and exact tool names;
- `tools/call` result for a tool actually returned by `tools/list`;
- sanitized response summaries, timestamp, tested host/path, and deployed commit.

A metadata endpoint returning HTTP 200 is not proof of an OAuth flow.

## OAuth 2.1 + PKCE acceptance

Do not mark OAuth/PKCE PASS based on discovery metadata. A valid end-to-end
test must use a real test client and a configured authorization server and
prove the authorization-code flow with:
- authorization request containing a fresh `code_challenge` and
  `code_challenge_method=S256`;
- redirect to the registered redirect URI with an authorization code;
- token exchange with the matching `code_verifier`;
- rejection of a wrong verifier, reused/expired code, and unregistered redirect URI;
- protected MCP access with the issued access token and rejection without it;
- redacted evidence only. Never persist authorization codes, tokens, verifiers,
  client secrets, or private keys in CI artifacts.

If the environment lacks configured OAuth metadata, client registration,
redirect URI, or credentials, report BLOCKED and name the missing configuration;
do not invent it, create secrets, or weaken authentication to make tests pass.

## Cloud worker / family role

Treat the cloud worker as an untrusted executor: accept only signed/authorized
jobs, use least privilege, attach job ID + commit SHA to reports, enforce time
and resource limits, and return sanitized artifacts. The Brain supervisor
retains scheduling and approval authority; workers do not self-authorize deploys.
Use simulation first. Family/household roles are governance/approval roles only
if explicitly configured in the product; never infer identity or grant access
based on a label. Require explicit authorization for consequential operations.

## Release gate

Overall integration is PASS only when all four independent evidence groups
pass: live MCP handshake/list/call, OAuth 2.1 + PKCE end-to-end negative and
positive tests, software ASIC simulation report, and cloud-worker job provenance.
Local simulator success cannot substitute for live-service evidence.
