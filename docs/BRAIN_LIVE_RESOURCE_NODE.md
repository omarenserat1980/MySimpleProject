# Brain Live Resource Node

This zero-cost-first agent measures resources on the host where it is actually run. It is a separate local process, not a simulated hardware catalog entry.

## 1. Dry-run on the real host

From the repository root, run in Termux or another Python environment:

```bash
python -m brain_v12.tools.brain_live_resource_agent
```

This prints measured CPU count, available memory when exposed by the OS, disk availability, OS/architecture, Python version, and sample time. It makes no network request.

## 2. Send one authenticated heartbeat to Brain

The Brain API must already be running and the device bridge must be enabled with a valid server-side key. Configure the same key locally on the agent; do not put it in GitHub source, issue text, or logs.

```bash
export V12_BRAIN_URL="http://127.0.0.1:8012"
export V12_AGENT_ID="brain-resource-node-01"
export V12_AGENT_KEY="YOUR_LOCALLY_CONFIGURED_AGENT_KEY"
python -m brain_v12.tools.brain_live_resource_agent --send
```

For a remote Brain URL, HTTPS is required. Plain HTTP is accepted only for loopback hosts. The agent sends one heartbeat to `/api/device/heartbeat`; it does not poll for tasks, start mining, or run arbitrary commands. Server-side configuration must authorize the exact agent ID (prefer `BRAIN_AGENT_KEYS_JSON` for per-agent keys) or the configured shared key. Keep the key out of the repository.

## 3. Interpret the evidence honestly

- `DRY_RUN`: local metrics were collected; no connection was attempted.
- `heartbeat_acknowledged: true`: Brain accepted an authenticated heartbeat for that agent ID. This is evidence of a live connection at that time, not independent proof of the host's physical backing.
- `resource_verified`, `mining_verified`, and `revenue_verified` remain false. Resource metrics are self-reported. Mining requires pool-derived accepted-share evidence; revenue requires independent payout records and cost accounting.
- HTTP errors, missing keys, unavailable metrics, and connection failures remain failures; do not convert them to success.

This agent does not provision a cloud machine. It uses an already-authorized host and has no paid-resource fallback.
