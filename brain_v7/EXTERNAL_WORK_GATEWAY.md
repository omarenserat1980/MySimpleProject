# External Work Gateway V1

The Brain now contains a permission-gated control plane for legitimate external
work. It is designed for user-owned accounts on platforms such as Upwork,
Fiverr, Freelancer, Mostaql, Khamsat, and LinkedIn.

## Workflow

1. Register an account without storing passwords or 2FA secrets.
2. Ingest opportunities through an approved/public/authorized connector.
3. Route each opportunity to a suitable employee.
4. Draft a proposal.
5. Keep submission in **AWAITING_APPROVAL** until the user/platform grants the
   required authorization.
6. Record an order only after a real order exists.
7. Track production and QA externally or through future adapters.
8. Verify payment using transaction/order evidence.
9. Count only verified payments as realized revenue.

## Safety gates

- No credential storage.
- No password or 2FA handling.
- No money transfers or withdrawals.
- No contract signing by the Brain.
- No spam or unsolicited mass submissions.
- No bypassing platform rules, identity checks, or rate limits.
- Stronger permissions than READ_ONLY/READ_AND_DRAFT are rejected by the
  gateway.
- Revenue is not counted until payment evidence is supplied.

This system increases operational capability but does not guarantee income.
