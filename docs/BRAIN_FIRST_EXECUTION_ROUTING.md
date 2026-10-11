# Brain-first execution routing

Electronic Brain-owned execution paths are the default. Desktop Commander is an
optional, quota-limited administrative fallback, not a dependency for Brain.

## Channel order

1. `brain_local` — existing Brain runtime and local tools.
2. `github_actions_arkan` — free self-hosted GitHub Actions runner on Arkan,
   only when a recent runner status proves it is online.
3. `termux_agent` — enrolled Android agent (Redmi/Realme), only after a fresh
   authenticated heartbeat proves it is online.
4. `desktop_commander` — fallback only when its quota is explicitly available.

Unknown, stale, unauthenticated, or unmeasured channels must be marked
unavailable. Never infer a live device from a passing unit test or server
readiness response. If no channel is verified, stop with
`NO_VERIFIED_EXECUTION_CHANNEL` instead of silently switching to a paid
service or claiming that work ran.

## Routing helper

`brain_v12/tools/brain_execution_priority.py` chooses a route from explicit
JSON evidence. It is a policy resolver, not a remote executor; the selected
Brain adapter must still perform the work and return execution evidence.

Example:

```json
{
  "channels": {
    "brain_local": {"available": true, "reason": "runtime readiness verified"},
    "github_actions_arkan": {"available": false, "reason": "runner offline"},
    "termux_agent": {"available": false, "reason": "no fresh heartbeat"},
    "desktop_commander": {"available": false, "quota_available": false}
  }
}
```

Pipe this evidence to the helper or pass it using `--evidence path.json`.
Do not include credentials or tokens in the evidence file.

## Validation

```sh
python -m unittest brain_v12.tests.test_brain_execution_priority -v
```

This change does not merge PR #405 and does not establish a live connection to
Arkan or either Android device. Real device acceptance still requires fresh,
authenticated heartbeat evidence and measured capacity.
