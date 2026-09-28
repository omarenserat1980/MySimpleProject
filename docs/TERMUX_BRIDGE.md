# V12 BRAIN Termux Emulator outbound bridge

The BRAIN Termux Emulator device does **not** expose a public listening port.

The architecture is:

1. Brain V12 running from the GitHub-managed application queues an allowlisted device task.
2. BRAIN Termux Emulator makes an outbound HTTPS poll to `/api/device/poll`.
3. BRAIN Termux Emulator authenticates with the shared secret configured as `BRAIN_EMULATOR_AGENT_KEY` in the runtime secret store.
4. BRAIN Termux Emulator executes only fixed tasks; arbitrary shell commands are rejected by design.
5. BRAIN Termux Emulator posts the result to `/api/device/report`.
6. Brain V12 verifies the task/agent match and exposes the result to the cognitive loop.
7. The cognitive loop verifies the completed result and records the next state/lesson.

## BRAIN Termux Emulator setup

Create a key locally and never paste it into chat:

```bash
mkdir -p ~/v12-agent
pkg install openssl-tool -y
openssl rand -hex 32 > ~/v12-agent/agent.key
chmod 600 ~/v12-agent/agent.key
```

The same secret must be configured in Render as `BRAIN_EMULATOR_AGENT_KEY`.

Run:

```bash
cd ~/v12-agent
python agent.py
```

Environment variables:

- `V12_BRAIN_URL`: Brain URL.
- `V12_AGENT_ID`: unique device ID.
- `V12_AGENT_KEY_FILE`: local key file path.
- `V12_POLL_SECONDS`: polling interval.

No inbound BRAIN Termux Emulator port or public shell is required.
