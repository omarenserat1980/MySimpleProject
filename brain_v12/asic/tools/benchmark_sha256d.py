#!/usr/bin/env python3
"""Measure host-CPU hashlib SHA256d throughput; not an ASIC or mining claim."""
import argparse
import hashlib
import json
import time

HEADER_PREFIX = bytes.fromhex(
    "01000000" + "00" * 32
    + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa"
    + "4b1e5e4a29ab5f49ffff001d"
)
assert len(HEADER_PREFIX) == 76


def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def benchmark(count: int) -> dict:
    if count < 1 or count > 10_000_000:
        raise ValueError("count must be in range 1..10000000")
    start = time.perf_counter()
    checksum = b""
    for nonce in range(count):
        header = HEADER_PREFIX + nonce.to_bytes(4, "little")
        checksum = double_sha256(header)
    elapsed = time.perf_counter() - start
    return {
        "benchmark": "python_hashlib_sha256d_header",
        "execution": "host_cpu_software",
        "hashes": count,
        "elapsed_seconds": round(elapsed, 6),
        "hashes_per_second": round(count / elapsed, 2) if elapsed else None,
        "last_digest_hex": checksum.hex(),
        "nonce_range": [0, count - 1],
        "is_live_mining": False,
        "is_rtl_or_asic_measurement": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count), sort_keys=True))


if __name__ == "__main__":
    main()
