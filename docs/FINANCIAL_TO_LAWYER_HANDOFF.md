# Financial → Lawyer Handoff

When Brain has independently verified positive funds, it may open the legal
handoff state and prepare a request for an already-authorized human lawyer.

Flow:

`VERIFIED_FUNDS → LEGAL_HANDOFF_PENDING`

The trigger requires:
- independently verified funds;
- positive available amount;
- funding evidence references;
- verified contracting/legal authority.

The system does **not**:
- choose or invent a lawyer;
- determine heirs or beneficiaries;
- disclose private identity/payment data;
- initiate a transfer;
- treat a planned request as a completed payment.

The lawyer must independently verify authority, beneficiaries where applicable,
destination, jurisdiction, and transfer requirements before any lawful transfer.

Private references such as `FOUNDER_IDENTITY_REF` and
`LAWYER_CONTACT_REF` are used instead of raw personal data.
