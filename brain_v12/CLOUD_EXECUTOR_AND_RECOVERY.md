# Brain Cloud Executor — Piece 5

Initial contract-only skeleton. It never launches commands, provisions infrastructure,
or connects to a cloud account. Requests remain blocked unless identity, resource,
permission, and zero-cost checks are explicitly supplied; even then the prototype
returns ACCEPTED_FOR_REVIEW and does not execute. Paid fallback is not allowed.

# Verification & Recovery — Piece 6

Initial local artifact-digest verifier and bounded retry planner. The verifier
checks SHA-256 against a caller-supplied expected digest. The planner returns a
decision only; it does not retry work or restore state. This is not a full signed
evidence chain or recovery engine.
