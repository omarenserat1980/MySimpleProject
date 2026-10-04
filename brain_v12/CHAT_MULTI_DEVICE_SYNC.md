# Brain Chat Multi-Device Sync

Brain Chat uses the Brain service as the shared conversation authority.

## Device model

Each client keeps a stable `device_id` and a local sync cursor. A device:

1. writes messages with a stable `client_message_id`;
2. retries writes when offline;
3. reconnects to the same Brain Chat API;
4. reads `GET /api/brain-chat/sessions/{session_id}/sync?after=<cursor>`;
5. advances its cursor only after applying the returned events successfully.

## Guarantees

- Append-only conversation events.
- Cursor-based incremental replay.
- Idempotent client message identity.
- Offline-first retry semantics.
- Existing durable server-side session/message store remains authoritative.
- The synchronization runtime's fail-closed evidence rules remain separate from chat presentation.

## Important deployment rule

Cross-device synchronization is real only when devices authenticate to the **same persistent Brain Chat backend**. A static browser page with an independent local database cannot synchronize with another device by itself.

The next integration step is to make the Brain AI web client automatically persist its device ID, maintain the cursor, push offline writes, pull the event feed after reconnect, and expose a "Synced" state backed by the server cursor/evidence.
