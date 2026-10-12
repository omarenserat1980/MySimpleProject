# Brain Legal / Human Handoff Policy

## Purpose
Provide an evidence-first, privacy-preserving path for future human legal assistance, estate administration, and lawful transfer of verified company/founder funds.

## Core rule
Brain may prepare, organize, verify, and document a handoff. Brain MUST NOT independently appoint a lawyer, determine heirs, sign a legal mandate, make a personal guarantee, or transfer funds solely because a trigger was detected.

## Lifecycle
VERIFIED_FUNDS
-> LEGAL_HANDOFF_PENDING
-> LAWYER_CANDIDATE_REVIEW
-> LAWYER_AUTHORITY_VERIFIED
-> BENEFICIARY_AUTHORITY_VERIFIED
-> HUMAN_HANDOFF
-> HANDOFF_EVIDENCE_RECORDED
-> CLOSED

Exceptional states:
BLOCKED, DISPUTED, EXPIRED, REJECTED, CANCELLED.

## Identity privacy
- Use FOUNDER_IDENTITY_REF, never the underlying national ID/passport value in source, CI logs, issues, artifacts, or public pages.
- The private identity record belongs in an authorized encrypted/private store.
- Evidence records contain only opaque references, hashes, timestamps, status, and authority metadata.
- A matching identity record is not by itself proof of legal authority.

## Lawyer verification
Before a lawyer is treated as authorized, the system must have independent evidence appropriate to the jurisdiction:
- identity of the lawyer;
- professional/license or registration evidence where applicable;
- jurisdiction;
- authority/mandate scope;
- effective date and expiry where applicable;
- independent verification source;
- handoff reference.

If any required authority evidence is missing or contradictory, the state remains BLOCKED.

## Beneficiary / estate verification
Brain must not infer heirs from private conversation, account ownership, nationality, religion, or family claims. Beneficiary authority requires appropriate legal documentation and jurisdiction-specific verification.

## Money transfer
- Verified funds remain distinct from legal authority.
- No transfer occurs merely because VERIFIED_FUNDS exists.
- Payment execution requires the applicable payment policy, authorization, destination verification, reconciliation, and evidence.
- Personal and company funds must remain separated.
- No private payment destination is committed to source control.

## Audit
Every transition records:
event_id, state, timestamp, actor class, policy version, evidence references, and decision reason.
Never record raw identity numbers, account credentials, private keys, or authentication secrets.

## Fail closed
If legal authority, identity provenance, beneficiary authority, or payment reconciliation cannot be verified, the handoff is BLOCKED.
