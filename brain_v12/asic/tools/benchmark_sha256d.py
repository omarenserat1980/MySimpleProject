#!/usr/bin/env python3
"""Measure host-CPU hashlib SHA256d throughput; not an ASIC or mining claim."""
import argparse
import hashlib
import json
import statistics
import time

HEADER_PREFIX = bytes.fromhex(
    "01000000" + "00" * 32
    + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa"
    + "4b1e5e4a29ab5f49ffff001d"
)
assert len(HEADER_PREFIX) == 76


def double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def run_sample(count: int) -> tuple[float, str]:
    start = time.perf_counter()
    digest = b""
    for nonce in range(count):
        digest = double_sha256(HEADER_PREFIX + nonce.to_bytes(4, "little"))
    elapsed = time.perf_counter() - start
    return elapsed, digest.hex()


def benchmark(count: int, repeats: int = 3) -> dict:
    if count < 1 or count > 10_000_000:
        raise ValueError("count must be in range 1..10000000")
    if repeats < 1 or repeats > 9:
        raise ValueError("repeats must be in range 1..9")
    # Warm up interpreter and hashlib before recording samples.
    run_sample(min(count, 100))
    samples = []
    last_digest = ""
    for _ in range(repeats):
        elapsed, last_digest = run_sample(count)
        samples.append({
            "elapsed_seconds": round(elapsed, 6),
            "hashes_per_second": round(count / elapsed, 2) if elapsed else None,
        })
    rates = [item["hashes_per_second"] for item in samples if item["hashes_per_second"] is not None]
    return {
        "benchmark": "python_hashlib_sha256d_header",
        "execution": "host_cpu_software",
        "hashes_per_sample": count,
        "repeats": repeats,
        "samples": samples,
        "median_hashes_per_second": round(statistics.median(rates), 2) if rates else None,
        "last_digest_hex": last_digest,
        "nonce_range_per_sample": [0, count - 1],
        "is_live_mining": False,
        "is_rtl_or_asic_measurement": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count, args.repeats), sort_keys=True))


if __name__ == "__main__":
    main()
