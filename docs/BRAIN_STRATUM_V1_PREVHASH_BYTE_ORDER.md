# Stratum V1 previous-hash byte order

## What is now implemented

`stratum_v1_prevhash_to_header_wire_hex()` implements one explicitly named legacy Stratum V1 convention: the 32-byte `mining.notify` `prevhash` is represented as eight little-endian 32-bit words. The normalizer reverses bytes within each four-byte word. It deliberately does **not** reverse all 32 bytes and does not auto-detect the encoding.

## Regression vector

The test uses the `mining.notify` example for block 672486 discussed at [Stack Overflow: “Hash of previous block” from Stratum protocol](https://stackoverflow.com/questions/66412968/hash-of-previous-block-from-stratum-protocol). The answer reports the eight-word representation and the corresponding displayed block hash. This is a useful regression vector, but it is community evidence—not a current Braiins Pool interoperability certification.

## Safe integration contract

- Call the normalizer only when the selected pool's protocol dialect is confirmed to match this legacy encoding.
- `prepare_and_search_job()` still requires an explicit `prevhash_wire_hex`; it never silently applies a pool-specific conversion.
- The remaining coinbase/Merkle/header pipeline must be validated against a complete, independently sourced known job before any live pool adapter is considered.
- No network transport, credentials, share submission, pool acceptance, or revenue verification is enabled by this change.
