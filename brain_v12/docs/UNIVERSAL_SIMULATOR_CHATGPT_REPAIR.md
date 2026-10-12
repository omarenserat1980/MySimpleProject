# Universal Simulator Registry and ChatGPT Brain Repair Center

## Purpose

Electronic Brain's supported simulators share one diagnostic and AI repair-planning service. The service discovers repository evidence for known simulator families, accepts custom simulator registrations, normalizes and redacts error reports, and asks the configured OpenAI-compatible provider for a structured repair proposal.

**Registration is not connectivity.** A repository path is discovery evidence only. A registered external service is marked `NOT_PROBED` until an authorized, explicit health probe is implemented and passes. The service does not execute AI-generated scripts or patches.

## API

All control-plane routes require the configured `BRAIN_CONTROL_KEY` in the `X-Brain-Control-Key` header.

- `GET /api/simulators/registry` — discovered and registered simulator inventory.
- `POST /api/simulators/register` — register a custom adapter or simulator identity.
- `GET /api/brain-repair/status` — report registry count and provider configuration status.
- `POST /api/brain-repair/analyze` — send a sanitized incident to the configured provider for diagnosis and a repair proposal.
- `POST /api/errors/report` — legacy/common error intake; accepts known simulator IDs and forwards reports to the shared repair analysis service when configured.
- `GET /api/errors/recent` — retrieve recent error reports.

### Register a custom simulator

```json
{
  "simulator_id": "my-render-adapter",
  "name": "My Render Adapter",
  "kind": "cloud_deployment",
  "version": "1.0",
  "execution_mode": "EXTERNAL",
  "capabilities": ["health_check", "diagnostics", "error_reporting"],
  "adapter_status": "PARTIAL"
}
```

The registration endpoint records metadata only. It does not contact an endpoint, authenticate to a cloud service, or prove that the simulator is running. Supported execution modes are `SIMULATED`, `EXTERNAL`, `LOCAL`, and `UNVERIFIED`.

### Submit a diagnostic incident

```json
{
  "simulator_id": "render-brain",
  "source_component": "deployment",
  "error_type": "DeploymentTimeout",
  "error_message": "Deployment health check timed out",
  "logs": "Sanitized, relevant log excerpt",
  "expected_behavior": "Service becomes healthy",
  "actual_behavior": "Health check timed out",
  "severity": "high",
  "context": {
    "component": "deployment-adapter",
    "operation": "health_check"
  }
}
```

The response distinguishes `AI_ANALYSIS_COMPLETED`, `NOT_CONFIGURED`, `AI_PROVIDER_FAILED`, and `AI_RESPONSE_INVALID`. Only a valid structured response from the configured provider is classified as completed.

## Provider configuration

The existing server-side `OpenAIProvider` is reused. Configure `OPENAI_API_KEY` in the deployment's secret store; optionally configure `OPENAI_BASE_URL` and `OPENAI_MODEL` according to the provider setup. Never place credentials in source control or client-side code.

If credentials are absent, the service records `NOT_CONFIGURED`; it does not label mock output as a real AI response. Provider reachability is not assumed from the presence of a key.

## Structured AI response

The provider is instructed to return a JSON object with:

- `root_cause_hypotheses`
- `evidence`
- `confidence`
- `recommended_actions`
- `required_tools`
- `proposed_files`
- `proposed_scripts`
- `test_plan`
- `rollback_plan`
- `risk_level`
- `requires_human_approval`

Responses missing required fields are rejected as `AI_RESPONSE_INVALID`.

## Security and execution boundary

- Error text, logs, stack traces, and repository content are untrusted input.
- Payloads are bounded and common secret-bearing fields and values are redacted before provider calls.
- The AI service proposes tools, scripts, and patches; it does not execute them.
- Execution requires a separate authorized adapter, isolated workspace, verification gate, and audit evidence.
- Production changes, destructive actions, privileged commands, secret changes, and protected-branch merges require explicit approval.
- Never interpret registry membership as evidence of a live external connection, a booted VM, or a real physical device.

## State and audit paths

Defaults are:

- Registry: `.brain/state/simulator-registry.json`
- AI repair analysis audit: `.brain/state/repair-analysis.jsonl`
- Existing error intake: `.brain/state/error-recovery.jsonl`

Override paths with `BRAIN_SIMULATOR_REGISTRY_PATH`, `BRAIN_REPAIR_AUDIT_PATH`, and `BRAIN_ERROR_STORE`. Use persistent writable storage for production deployments.

## Current scope and limitations

This integration provides registry discovery, custom registration, common error intake, real-provider analysis when configured, structured-response validation, and audit records. It does **not** claim that every external provider has a working adapter or that generated repairs have been executed. Those capabilities require adapter-specific integration and independently verifiable tests.
