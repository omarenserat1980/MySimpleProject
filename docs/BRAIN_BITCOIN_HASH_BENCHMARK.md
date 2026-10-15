# Brain Bitcoin Hash Benchmark

## What this adds
- A bounded, standard-library-only SHA-256d benchmark for an 80-byte synthetic block header.
- A measured local hashes/second result with explicit evidence labels.
- An API endpoint intended for diagnostics, not a mining executor.

## Run in Termux or repository Python environment
```sh
python -m pytest -q brain_v12/tests/test_bitcoin_hash_benchmark.py
python - <<'PY'
from brain_v12.brain.bitcoin_hash_benchmark import benchmark_header_hashing
print(benchmark_header_hashing(duration_seconds=1.0, max_hashes=100000))
PY
```

## Truth boundary
This benchmark does not create a valid Bitcoin block template or Stratum job, does not check the network/pool target, does not connect to a pool, does not submit shares, and does not earn BTC. It measures local Python/CPU SHA-256d throughput only. ASIC simulations and user-supplied hashrate values are not real measurements.

Bitcoin block headers are 80 bytes and proof of work is SHA256(SHA256(header)); see the [Bitcoin Developer Reference](https://developer.bitcoin.org/reference/block_chain.html) and [Mining Guide](https://developer.bitcoin.org/devguide/mining.html). A future pool worker must implement the chosen pool protocol correctly, validate jobs/targets, and prove accepted shares before any live-mining claim.
