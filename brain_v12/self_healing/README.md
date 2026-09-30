# Brain Continuous Self-Healing

The Brain repair cycle is:

`RUN -> OBSERVE -> DIAGNOSE -> REPAIR -> VERIFY -> RETRY`

Rules:

- A green repair command is **not** success.
- Success requires the target command and, when configured, the independent verification command to exit with code 0.
- Failures are persisted to `.brain/state/self_healing_history.json`.
- Attempts are bounded to prevent runaway loops.
- Backoff grows between attempts.
- Secrets are redacted from persisted environment diagnostics.
- The repair step is a replaceable Brain component. It can be a deterministic fixer today and an internal code-repair agent later.
- The supervisor itself does not use Render, Oracle Cloud, or Google Cloud.

Example:

```bash
python -m brain_v12.self_healing.supervisor \
  --command "python -m pytest -q" \
  --verify "python -m pytest -q" \
  --repair "python brain_v12/self_healing/repair.py"
```
