# Brain Leadership Contract

## Purpose

Prevent two Brain generations from acting as the active authority at the same
time. Leadership is separate from identity: identity proves what a runtime
claims to be; a leadership lease proves which runtime currently owns execution
authority.

## Required chain

Identity -> Golden Checkpoint -> Leadership Lease -> Fencing Token -> Executor

A runtime MUST validate its identity against the stable checkpoint before it
can acquire leadership.

## Lease rules

- Only one active lease exists in the backing store.
- A live lease blocks another acquisition.
- An expired lease may be replaced.
- Every replacement increments a monotonic fencing token.
- The old lease cannot renew or pass `assert_current` after replacement.
- Release is accepted only for the current lease holder.
- Malformed or ambiguous state must fail closed.

## Important limitation

The current implementation uses SQLite and is a **single durable control-plane
store**, suitable for one Brain control-plane host or a shared filesystem with
correct SQLite locking semantics. It does NOT claim distributed consensus
across independent cloud VMs.

Before multi-VM active/active Brain is enabled, replace or back the leadership
store with a genuinely shared transactional/consensus-capable authority and
retain the same lease/fencing contract.

## Security

Leadership records contain no passwords, API keys, tokens, or private keys.

A fencing token is an execution-authority token, not a secret. Executors must
eventually reject work carrying an obsolete token.

## Verification requirement

Leadership acquisition alone never proves Windows, QEMU, Cloud, or any other
capability. Capability-specific gates remain mandatory.
