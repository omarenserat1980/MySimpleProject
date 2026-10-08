# Electronic Brain MCP

This is a read-first MCP surface for Electronic Brain.

## Exposed tools

- `brain_status`
- `brain_device_status`
- `brain_evidence`
- `brain_chat`

The MCP surface does not create agent keys, change Android permissions, execute arbitrary shell commands, or replace the existing Brain app.

## Entry point

Run the wrapper instead of the normal app entrypoint:

```bash
uvicorn brain_v12.mcp_server:app --host 0.0.0.0 --port 10000
```

The MCP endpoint is:

```
/mcp
```

Set `BRAIN_MCP_TOKEN` before exposing it outside a trusted network.

## Verification boundary

A successful MCP handshake proves transport and tool discovery only.

A real `mcp_call` to `brain_device_status` with fresh device evidence is required before claiming that OpenAI is actively talking to the Brain runtime.
