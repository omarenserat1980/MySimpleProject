"""Pure coinbase assembly and Merkle folding primitives for mining jobs.

All hash byte strings are explicit byte sequences supplied by the caller. This
module does not infer Stratum/pool endianness, parse transactions, open sockets,
search nonces, or submit shares. Pool-specific conversion must be validated
against an authoritative known vector before live use.
"""
from __future__ import annotations

from brain_v12.brain.brain_owned_compute_runtime import double_sha256

MAX_COINBASE_BYTES = 1_048_576
MAX_MERKLE_BRANCHES = 4096


def _hex_bytes(value: bytes, field: str, *, maximum: int) -> bytes:
    if not isinstance(value, bytes):
        raise ValueError(f"{field}_MUST_BE_BYTES")
    if len(value) > maximum:
        raise ValueError(f"{field}_TOO_LARGE")
    return value


def assemble_coinbase(
    *, coinb1: bytes, extranonce1: bytes, extranonce2: bytes, coinb2: bytes
) -> bytes:
    """Concatenate decoded coinbase fragments in the exact supplied order."""
    parts = (
        _hex_bytes(coinb1, "COINB1", maximum=MAX_COINBASE_BYTES),
        _hex_bytes(extranonce1, "EXTRANONCE1", maximum=128),
        _hex_bytes(extranonce2, "EXTRANONCE2", maximum=128),
        _hex_bytes(coinb2, "COINB2", maximum=MAX_COINBASE_BYTES),
    )
    total = sum(map(len, parts))
    if total == 0 or total > MAX_COINBASE_BYTES:
        raise ValueError("COINBASE_SIZE_OUT_OF_RANGE")
    return b"".join(parts)


def fold_merkle_branches(
    *, coinbase_tx: bytes, branches_in_pool_order: tuple[bytes, ...] | list[bytes]
) -> bytes:
    """Compute SHA256d Merkle folding without silently reversing any byte string.

    `branches_in_pool_order` and the returned value preserve the byte order used
    by the caller. The result is not automatically converted to serialized
    Bitcoin-header order; that conversion is a pool-specific contract.
    """
    _hex_bytes(coinbase_tx, "COINBASE_TX", maximum=MAX_COINBASE_BYTES)
    if not coinbase_tx:
        raise ValueError("EMPTY_COINBASE_TX")
    if not isinstance(branches_in_pool_order, (tuple, list)):
        raise ValueError("MERKLE_BRANCHES_MUST_BE_SEQUENCE")
    if len(branches_in_pool_order) > MAX_MERKLE_BRANCHES:
        raise ValueError("TOO_MANY_MERKLE_BRANCHES")

    current = double_sha256(coinbase_tx)
    for branch in branches_in_pool_order:
        if not isinstance(branch, bytes) or len(branch) != 32:
            raise ValueError("MERKLE_BRANCH_MUST_BE_32_BYTES")
        current = double_sha256(current + branch)
    return current
