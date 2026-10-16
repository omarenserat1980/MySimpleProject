# Bounded nonce ranges and checkpoint-style resume

`partition_nonce_range(start_nonce, end_nonce_exclusive, partitions)` returns
balanced, deterministic, disjoint half-open ranges. The upper bound is
exclusive and may be `2**32`, allowing the final uint32 nonce to be included.
Empty ranges are omitted when there are more partitions than nonce values.

The primitive is metadata only: it starts no threads or background jobs and
claims no mining performance. A bounded `search_nonce` call that exhausts its
configured hash count can be resumed at `start_nonce + hashes_checked`; this
is valid only for a no-hit result and for the exact header/target/job that was
used by the previous chunk. A production checkpoint must also bind those values
and the job identity, and must be authenticated before reuse. These tests prove
local range arithmetic and resume boundaries only; they do not establish pool
connectivity, accepted shares, or revenue.

Run:

```sh
python -m pytest -q \
  brain_v12/tests/test_nonce_range_partition_resume.py \
  brain_v12/tests/test_brain_owned_compute_runtime.py \
  brain_v12/tests/test_stratum_v1_end_to_end_fixture.py \
  brain_v12/tests/test_stratum_candidate_pipeline.py
```

## Bound checkpoint contract

The follow-up checkpoint helpers bind the job ID, SHA-256 fingerprint of the
80-byte header, exact target, start nonce, number of hashes checked, and next
nonce. They reject a hit result, changed job/header/target, malformed fields,
range arithmetic inconsistencies, and nonce-space exhaustion. The checkpoint
explicitly marks itself `authenticated: false`: it is not a signed token and
must not be trusted across process boundaries until a separate signature/MAC
or trusted storage layer is implemented and verified.

## Optional authenticated checkpoint contract

`sign_nonce_search_checkpoint` and `validate_authenticated_nonce_search_checkpoint`
add HMAC-SHA256 authentication for persistence or transfer when the caller has a
trusted secret provider. The key is supplied by the caller, must be at least 32
bytes, and is never generated or persisted by this module. The signed contract
uses a deterministic JSON representation and rejects unknown fields, tampering,
wrong keys, malformed tags, and unsigned checkpoints. HMAC requires the signer
and verifier to share a secret; it does not provide non-repudiation or solve key
rotation/distribution. Do not use a test key in production. No production key,
secret, or storage backend is configured by this change, and no checkpoint is
used to start compute automatically.
