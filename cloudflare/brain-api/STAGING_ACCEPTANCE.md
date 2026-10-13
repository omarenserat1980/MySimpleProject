# PayTabs + D1 Staging Acceptance Runbook

This runbook is an acceptance checklist, not evidence that a deployment or payment has occurred.

## Safety boundary

- Do not run the production deployment workflow to test a pull-request head. The production workflow checks out `main`.
- Use a dedicated staging Worker, a dedicated D1 database, and PayTabs Sandbox credentials only.
- Never copy production payment data into staging. Never print credentials or callback signatures in logs.
- Keep the revenue gate closed until every evidence item below is attached to the pull request and tied to the deployed commit and Actions run.

## Required isolated configuration

Configure GitHub Actions secrets/variables for a dedicated staging environment, not the production deploy job:

- Cloudflare API token limited to the required staging resources.
- Cloudflare account ID.
- Dedicated staging D1 database ID/name.
- Dedicated staging Worker name and URL.
- PayTabs Sandbox server key and Sandbox profile ID.
- A restricted staging origin/control token if required by the Worker.

If any required item is absent or the credentials cannot be confirmed as Sandbox-only, stop. Do not fall back to production credentials.

## Required test sequence

1. Deploy the exact PR head to the isolated staging Worker and record the commit SHA, deployment run ID, Worker URL, and deployment version.
2. Apply migrations only to the dedicated staging D1 database; capture the migration output and resulting migration list.
3. Verify Worker health and that no endpoint returns secrets.
4. Create a Sandbox order and record its order ID, expected amount, currency, and Sandbox transaction reference.
5. Deliver the valid PayTabs Sandbox callback and verify D1 records the payment as verified while revenue remains `PAYMENT_VERIFIED_PENDING_DELIVERY`.
6. Replay the same callback. Verify no duplicate payment event, order, or revenue-ledger row is created.
7. Try mismatched amount, mismatched currency, wrong order, and invalid signature. Each must fail closed and must not realize revenue.
8. Attempt delivery confirmation before verified payment; it must fail without changing the ledger.
9. Confirm delivery after verified payment. Verify delivery is `DELIVERED`, order is `COMPLETED`, and exactly one ledger row transitions to `REVENUE_REALIZED`.
10. Replay delivery confirmation and race two confirmations. Only one confirmation may succeed; a losing request must return a conflict and must not report a second successful realization.
11. Export sanitized Worker logs, D1 query results, callback response codes, test outputs, and workflow metadata. Remove tokens, keys, signatures, personal data, and any payment-instrument data before attaching.

## Evidence required for acceptance

- Passing CI on the exact PR head.
- Staging deployment run and URL, with commit SHA.
- D1 migration evidence for the isolated database.
- Sandbox transaction reference and callback verification evidence.
- Before/after D1 rows for payment, order, delivery, and revenue ledger.
- Callback replay and invalid-input rejection results.
- Delivery replay/concurrency result proving exactly-once revenue realization.
- Artifact or repository evidence with workflow run ID, commit SHA, timestamps, and sanitized logs.

## Acceptance rule

Do not merge or declare the payment/revenue phase complete until a reviewer can trace all evidence above. Unit, static, or SQLite tests alone are not a deployed D1/Worker integration test and are not proof of a real Sandbox transaction.
