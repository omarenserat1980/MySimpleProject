# Offline Stratum V1 end-to-end regression vector

This fixture validates the local data path from a synthetic nine-field
`mining.notify` parameter list through coinbase reconstruction, two Merkle
branches, an explicitly supplied serialized previous-hash, an 80-byte header,
and a bounded SHA256d nonce check.

## Evidence boundary

- The notify payload is synthetic test data, not a captured pool job.
- `prevhash_wire_hex` is deliberately supplied explicitly; the fixture does not
  infer or certify a pool-specific byte-order convention.
- The expected coinbase, raw Merkle root, header bytes, and displayed SHA256d
  hash are pinned as literals and were independently calculated with Python's
  `hashlib` double-SHA256 operation.
- The test uses the maximum valid 256-bit share target to test assembly and hash
  consistency, not realistic mining difficulty or performance.
- No socket, credentials, pool session, share submission, acceptance, or revenue
  is involved. A passing test is local regression evidence only, not proof of
  Braiins Pool interoperability or real mining.

Run the focused suite with:

```sh
python -m pytest -q \
  brain_v12/tests/test_stratum_v1_end_to_end_fixture.py \
  brain_v12/tests/test_bitcoin_header.py \
  brain_v12/tests/test_stratum_candidate_pipeline.py \
  brain_v12/tests/test_stratum_v1_jobs.py \
  brain_v12/tests/test_stratum_v1_protocol.py \
  brain_v12/tests/test_brain_owned_compute_runtime.py
```
