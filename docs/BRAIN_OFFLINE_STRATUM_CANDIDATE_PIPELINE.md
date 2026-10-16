# Brain Offline Stratum Candidate Pipeline

## Scope

`stratum_candidate_pipeline.py` integrates validated Stratum V1 job parsing, coinbase/extranonce construction, raw merkle-root calculation, explicit 80-byte header assembly, and bounded SHA256d nonce search. The share target is a separate required argument; it is not silently derived from `nBits` because pool share difficulty and Bitcoin network difficulty are distinct.

## Byte-order contract

The caller must provide `prevhash_wire_hex` already normalized to the serialized header byte order. No Stratum-specific byte-order guess is made. Before any live adapter can be considered, the selected pool's documented format must be covered by known vectors that verify prevhash, merkle branches, header bytes, and hash output.

## Safety and evidence

- Offline deterministic helper only; no networking, credentials, persistence, background worker, or share submission.
- Search is bounded by `max_hashes` and the underlying runtime's hard cap.
- A candidate is re-hashed and revalidated before it is returned.
- `NONCE_FOUND_UNSUBMITTED` proves only that the candidate header hash meets the caller-supplied target.
- Pool acceptance, real mining, and revenue remain false until independently evidenced; no payout or revenue is inferred from local hashes.
- Android/Termux remains a gateway, not a compute host. CI is not a mining host.
