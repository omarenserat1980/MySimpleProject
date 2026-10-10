# Electronic Brain runtime storage paths

Electronic Brain may run from a source checkout that is read-only to the process
user (for example, when a runner checkout contains files owned by root). Runtime
state should not be created under the source tree by default.

## Defaults

The application initializes runtime paths before importing modules that create
state during import. The default runtime root is:

`~/.brain/runtime`

It can be changed with `BRAIN_RUNTIME_HOME`. Explicit path overrides take
precedence over defaults:

- `BRAIN_DB`: main SQLite database
- `BRAIN_SYNC_QUEUE`: durable synchronization JSONL queue
- `BRAIN_GIT_ROOT`: workflow and Git-operation state
- `BRAIN_EVIDENCE_DB`: evidence SQLite database
- `BRAIN_MEDIA_ROOT`: media workspace

These paths are persistent state, not source code. Ensure the account running
the service owns the configured runtime root and has enough free disk space.

## Existing state and migration

Changing defaults does **not** automatically migrate an existing database,
queue, evidence store, or workflow directory from the source checkout. Before
switching an existing deployment, take a verified recovery snapshot and plan
a controlled migration of the state files. Do not delete the old state until
the new runtime has been verified against expected records.

## Verification

Run the runtime-path unit tests and the project's app import/smoke tests under
the same account and environment used by the service. A successful import alone
does not prove that the API is listening or authenticated; verify the configured
health and readiness endpoints separately.
