# Electronic Brain runtime storage paths

Electronic Brain can run from a source checkout that is readable but not writable
to the service account. Runtime state must not be created under the source tree by
default.

## Runtime root and path settings

The default writable state root is `~/.brain/runtime`. Set
`BRAIN_RUNTIME_HOME` to choose another writable location. Explicit settings are
preserved and take precedence:

- `BRAIN_DB`: main SQLite database
- `BRAIN_SYNC_QUEUE`: durable synchronization JSONL queue
- `BRAIN_GIT_ROOT`: workflow state and Brain Git workspace
- `BRAIN_EVIDENCE_DB`: evidence SQLite database
- `BRAIN_MEDIA_ROOT`: media input workspace
- `BRAIN_MEDIA_OUTPUT_ROOT`: generated media output workspace
- `AGENT_SANDBOX`: bounded code-execution sandbox
- `BRAIN_SUPERVISOR_ROOT` and `BRAIN_SUCCESS_BOT_ROOT`: supervisor and SuccessBot state directories
- `BRAIN_VIRTUAL_TASK_DB`: virtual task queue SQLite database

New renders are written below `BRAIN_MEDIA_OUTPUT_ROOT`; legacy media inputs remain
available at their existing location when the legacy media directory is present.
This avoids creating files under a source checkout merely to process existing inputs.

## First-start migration

When an individual `BRAIN_*` setting is not explicitly configured, startup uses
the writable runtime root and performs a conservative first-start copy of the
corresponding legacy state **only if the destination does not already exist**.
SQLite databases use SQLite's backup API; JSONL queue files use file copies; the
workflow, sandbox, supervisor, SuccessBot and media directories are copied as trees. Existing source files are not deleted
or overwritten. An already existing runtime destination wins and is never replaced.

This protects originals from deletion, but a migration is not a substitute for a
verified recovery snapshot. Before production rollout, confirm that the service is
stopped, snapshot current state, inspect the resulting destination databases and
queue, and verify expected record counts and workflows. If explicit `BRAIN_*`
overrides are configured, the corresponding automatic migration is skipped.

## Verification

Run `python -m unittest brain_v12.tests.test_runtime_paths -v` and the project's
app-import/startup smoke tests as the same account and environment used by the
service. A successful import alone does not prove the API is listening or
authenticated; verify health and readiness endpoints separately.
