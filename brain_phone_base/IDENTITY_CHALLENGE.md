# Brain Phone Base: Identity Challenge Protocol

## Purpose

This module adds a fail-closed verifier for a signed challenge/response bound to
one measurement SHA-256. It is protocol groundwork, not proof that the phone's
identity is independently verified.

## Security boundaries

- The challenge must be signed by an independent verifier. Pin that verifier's
  Ed25519 public key out-of-band; do not accept a verifier key supplied by the
  challenge itself.
- The device public key must come from a separately trusted enrollment process.
  Do not trust a public key merely because the phone includes it in its response.
- The response signature must be produced by a companion Android application
  using a key created and held by Android Keystore. Plain Python/Termux code
  cannot itself claim that a key is hardware-backed.
- Validate Android Key Attestation and its certificate chain, security level,
  application identity, verified-boot/device-lock state (where supported), and
  challenge binding on a trusted verifier before making an identity decision.
- Enforce one-time challenge IDs in durable verifier-side storage. The optional
  `seen_challenge_ids` set in this library is only a caller-supplied replay
  check; it is not durable by itself.
- Challenge signing and device signing are distinct trust roles. The device
  response signs the canonical JSON object returned to the caller; signatures
  use Ed25519 and base64 encoding.
- The module refuses expired challenges, challenges with a lifetime above five
  minutes, short nonces, mismatched measurement hashes, wrong key fingerprints,
  replayed IDs (when the caller supplies the seen set), and altered response
  fields.

## Current result semantics

Even if both signatures validate, the result is
`SIGNATURE_VALID_IDENTITY_UNVERIFIED`. The module always returns
`device_identity_verified=false`, `trusted=false`, `active=false`,
`manual_approval=NOT_GRANTED`, and `mining=DISABLED`. It does not register
the node, upload evidence, activate a node, or contact a mining pool.

A valid signature proves possession of the corresponding private key for that
message. It does not by itself prove that the key is hardware-backed, belongs to
a particular physical phone, or that the measurements are truthful.

## Android Keystore availability

A Python process in Termux does not directly expose the Android Keystore API as
a standard Python interface. The actual signer should be implemented in a
small Android companion app using Android Keystore, then provide a public-key
and attestation chain to the independent verifier. This repository change does
not yet implement that Android app or validate Android Key Attestation chains.

## Inputs expected by the verifier

- `challenge`: JSON object with schema, unique challenge ID, at least 32 bytes
  of random nonce (hex), issue/expiry timestamps, enrolled device key ID, and
  measurement SHA-256.
- `challenge_signature_b64`: Ed25519 signature over canonical JSON of challenge.
- `pinned_verifier_public_key_pem`: out-of-band trusted verifier public key.
- `response`: response JSON echoing challenge ID, nonce, device key ID and
  measurement hash, plus a signed timestamp.
- `response_signature_b64`: Ed25519 signature over canonical JSON of response.
- `enrolled_device_public_key_pem`: public key retrieved from trusted enrollment,
  not accepted solely from the response.
- `expected_measurement_sha256`: hash calculated independently by the verifier.

No endpoint or network transport is included. Keep all operations local until
the independent verifier, enrollment, attestation, replay protection, and manual
approval process have been reviewed and tested.
