# Brain Chat Legacy Session Recovery Runbook

## Purpose

Inventory and recover legacy chat sessions whose `chat_sessions.account_id` is NULL or blank, without guessing ownership or exposing message content.

## Safety rules

- Use the exact SQLite database file opened by the running Brain process (`BRAIN_DB`, or the configured default). Do not run against a newly created or copied empty database and treat that result as authoritative.
- Stop or quiesce writes to the database during an ownership recovery window.
- Make a verified, restorable database backup before applying any ownership mapping.
- Inventory is read-only. It reports session IDs and metadata only; it never returns message bodies.
- The mapping must be based on trusted external evidence and reviewed by an operator. Never infer ownership from message text, a device label, or whichever account asks first.
- Applying the map requires an explicit confirmation phrase, actor, and reason. All assignments are one SQLite transaction and produce rows in `chat_session_ownership_audit`.
- Already-owned sessions and unknown session IDs cause the whole operation to fail without partial assignments.
- This utility does not provision credentials, deploy code, or make the runtime production-ready.

## Step 1: read-only inventory

From the repository root, using the same Python environment as Brain:

```bash
python -m brain_v12.brain.chat_legacy_recovery --db /absolute/path/to/brain_v12.db inventory --output legacy-session-inventory.json
```

Review the report and preserve it with the recovery ticket. Do not publish it publicly; session IDs and device metadata are operational data.

## Step 2: prepare an explicit ownership map

Create a JSON object mapping only verified unowned session IDs to their intended account IDs:

```json
{
  "verified-session-id-1": "operator-assigned-account-a",
  "verified-session-id-2": "operator-assigned-account-b"
}
```

The file must not include sessions already owned. The operator must independently verify each mapping and document the evidence in the reason/ticket reference.

## Step 3: backup and apply

After a tested backup and a maintenance window, run:

```bash
python -m brain_v12.brain.chat_legacy_recovery --db /absolute/path/to/brain_v12.db apply \
  --mapping reviewed-ownership-map.json \
  --confirm ASSIGN_EXPLICIT_OWNERSHIP \
  --actor operator-id \
  --reason "recovery-ticket-or-evidence-reference"
```

The script fails closed without the exact confirmation phrase. Review the output and audit table. If any ownership is disputed, do not include that session in the map.

## Step 4: verify

Run inventory again. The number of unowned sessions should decrease only by the number of approved mappings. Check the audit rows and test that a credential for account A cannot read, sync, compact, message, or alter memory for account B's session.

## Rollback

Do not blindly reverse ownership assignments. Use the audit rows and the verified backup to plan a reviewed correction. Any correction must be atomic, explicitly approved, and audited. Preserve the original audit records.

## Status

The inventory/recovery utility and unit tests are proposed on the stacked branch `brain/chat-legacy-session-recovery-20261010`. No production database has been inspected or changed by this change.
