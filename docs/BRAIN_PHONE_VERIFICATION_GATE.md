# Brain Phone verification gate

The verification gate performs **structural and safety validation only**. It is
not an independent verifier and must never be presented as device identity
verification, hardware attestation, proof of physical capacity, or proof of
mining/revenue.

## Contract

`validate_phone_evidence(payload)` checks required fields, expected evidence
labels, timestamp syntax, basic resource value bounds, and all safety flags.
Malformed, incomplete, or suspicious payloads fail closed. Even a valid result
always returns:

- `trust_state=UNTRUSTED`
- `independent_verification=false`
- `eligible_for_activation=false`
- `eligible_for_mining=false`

## Run tests

```bash
python -m unittest brain_v12.tests.test_brain_phone_verification_gate -v
```

## What independent verification still requires

A future verifier must use a trust anchor that is not controlled solely by the
phone being measured, verify a cryptographic device-bound challenge/response,
bind the evidence to a fresh nonce and timestamp, and define key enrollment,
revocation, replay protection, and audit procedures. A self-signed key or
self-reported JSON file alone is not independent proof. Until that design is
implemented and exercised against a real device, do not activate the node,
dispatch jobs, start mining, or connect to a pool.
