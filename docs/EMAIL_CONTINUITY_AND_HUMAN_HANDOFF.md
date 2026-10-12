# Brain Email Continuity and Human Handoff

## Email continuity

The Brain email channel is treated as a monitored operational dependency.

- Watchdog cadence: every 30 minutes.
- Secrets remain in GitHub Actions Secrets.
- A probe is considered verified only when the adapter receives both message_id and thread_id.
- Failed probes fail closed and leave CI evidence for diagnosis.
- The watchdog is bounded and does not retry indefinitely.
- Email failure must never be interpreted as payment, delivery, legal, or business success.
- A separate ChatGPT-side fallback monitor may notify the user when the email channel or watchdog is unhealthy.

## Recovery

Recovery order:

1. Verify configuration without exposing secrets.
2. Verify AgentMail reachability.
3. Verify the Brain email adapter.
4. Retry only within a bounded policy.
5. Record evidence.
6. Escalate through the fallback channel if email remains unavailable.

## Human legal/estate handoff

Brain must not independently select a lawyer, transfer money, prove inheritance, or decide who is an heir.

A future legal handoff may proceed only when there is verified evidence of:

- the relevant legal entity or estate authority;
- identity and authority of the human lawyer or authorized representative;
- applicable jurisdiction and legal mandate;
- beneficiary/heir documentation where required;
- verified funds and reconciliation;
- an auditable handoff record.

The intended lifecycle is:

VERIFIED_FUNDS -> LEGAL_HANDOFF_PENDING -> LAWYER_AUTHORITY_VERIFIED -> BENEFICIARY_AUTHORITY_VERIFIED -> HUMAN_HANDOFF -> HANDOFF_EVIDENCE_RECORDED

Money movement remains separately permission-gated. A lawyer is a human legal counterparty, not an autonomous Brain agent.

No public repository, CI log, or evidence artifact may contain private payment destinations, private keys, or sensitive inheritance documents.
