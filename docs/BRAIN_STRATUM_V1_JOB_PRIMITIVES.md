# Brain Stratum V1 Job Primitives (Offline Only)

## Scope

This module validates `mining.notify` job fields, assembles coinbase bytes from supplied coinbase fragments and extranonces, computes the raw SHA256d merkle accumulator, and correlates share-response IDs in memory. It has no socket, TLS, credentials, pool endpoint, worker loop, persistence, or automatic submission.

## Evidence and safety boundaries

- Parsing a job or constructing a candidate is not proof of mining.
- A Stratum response with `result: true` is reported only as `POOL_RESPONSE_SAYS_ACCEPTED`; independent authenticated pool evidence is still required.
- Mismatched response IDs do not consume pending share correlation state. Unknown, duplicate, rejected, and malformed responses fail closed.
- This module does not assemble a complete live-pool block header; prevhash and merkle byte-order transformations must be confirmed against the selected pool's documented protocol and known vectors before any live adapter is considered.
- No network contact, share submission, payout, or revenue claim is made.
