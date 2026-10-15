# Brain Phone Base: Identity Challenge Protocol

## Purpose

This work adds a fail-closed Python challenge/response verifier and an Android
Keystore signing helper. It is protocol groundwork, not proof that the phone's
identity is independently verified.

## Security boundaries

- The challenge must be signed by an independent verifier. Pin that verifier's
  public key out-of-band; do not accept a verifier key supplied by the challenge.
- The device public key must come from a separately trusted enrollment process.
  Do not trust a public key merely because the phone includes it in its response.
- `PhoneIdentityKeyStore.kt` requests a P-256 signing key in Android Keystore
  with an enrollment attestation challenge and returns the public key and
  certificate chain. The private key is not exported.
- The Android helper only requests and exports the chain; it does not validate
  the chain or claim that the key is hardware-backed. Unsupported devices fail
  closed when key generation/attestation fails.
- Validate Android Key Attestation and its certificate chain, security level,
  application identity, verified-boot/device-lock state (where supported), and
  challenge binding on a trusted verifier before making an identity decision.
- Enforce one-time challenge IDs in durable verifier-side storage. The optional
  `seen_challenge_ids` set in this library is only a caller-supplied replay
  check; it is not durable by itself.
- The verifier accepts Ed25519 or P-256 public keys. The Android helper signs
  response canonical JSON using `SHA256withECDSA`; challenge signatures may use
  a supported key type and base64 encoding.
- The module rejects expired/overlong challenges, short nonces, mismatched
  measurement hashes, wrong key fingerprints, replayed IDs (when supplied),
  altered response fields, and invalid signatures.

## Current result semantics

Even if both signatures validate, the result is
`SIGNATURE_VALID_IDENTITY_UNVERIFIED`. The verifier always returns
`device_identity_verified=false`, `trusted=false`, `active=false`,
`manual_approval=NOT_GRANTED`, and `mining=DISABLED`. It does not register
the node, upload evidence, activate a node, or contact a mining pool.

A valid signature proves possession of the corresponding private key for that
message. It does not by itself prove that the key is hardware-backed, belongs to
a particular physical phone, or that the measurements are truthful.

## Enrollment and response flow

1. An independent enrollment authority generates a fresh random challenge of at
   least 32 bytes and signs/records it.
2. A foreground user action calls `createEnrollmentKey(challenge)`. The helper
   refuses to overwrite an existing alias and returns the P-256 public key plus
   the Android certificate chain.
3. The independent verifier validates the chain and the attestation challenge,
   then records the enrolled public key and its fingerprint.
4. For a short-lived, signed challenge bound to a measurement hash, the Android
   app builds the response fields and calls `signResponse(fields)`. The caller
   sends the returned payload/signature to the independent verifier through a
   separately reviewed transport.
5. The verifier validates signatures, challenge freshness, replay state, key
   enrollment and measurement binding. Trust and activation remain blocked until
   the attestation policy and explicit manual approval both pass.

No endpoint, enrollment authority, certificate-chain validator, replay database,
or network transport is included in this change. Do not treat the helper alone
as completed independent identity verification.
