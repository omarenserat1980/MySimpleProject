# Brain Runtime Independence Contract

## Root rule

Brain production execution is owned by the Brain Internal Runtime. GitHub Actions is a source-of-truth, control-plane, evidence, and optional verification adapter; it is not a runtime fallback.

## Single execution authority

All production task admission must pass through:

Task -> Execution Gateway -> Internal Runner -> Verify -> Evidence -> Checkpoint

The gateway is fail-closed. If the Brain-owned runner cannot prove the required capability, the task is blocked rather than redirected to a hosted runner.

## Durable runtime

brain_v12/brain/internal_task_runtime.py provides a local durable queue, terminal state, restart-safe replay selection, and immutable evidence files. It does not call GitHub to execute work.

## Regression rule

Runtime workflows must not contain runs-on: ubuntu-latest. Runtime workflows must use the Brain-owned labels and internal-runner preflight.

Pure verification/control-plane workflows may use GitHub-hosted execution only when they do not perform production work. A future runtime workload must not create its own executor selection logic; it must use BrainExecutionGateway.

## Authority state

The system must distinguish:

- INTERNAL_RUNTIME_CODE_PRESENT
- INTERNAL_RUNNER_PREFLIGHT_VERIFIED
- INTERNAL_RUNNER_ONLINE
- TASK_EXECUTED
- TASK_VERIFIED
- AUTONOMOUS_WITHIN_AUTHORITY

Presence of code or configuration never proves the later states.
