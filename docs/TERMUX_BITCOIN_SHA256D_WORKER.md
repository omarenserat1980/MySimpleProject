# Termux Bitcoin SHA-256d Worker

Status: implementation scaffold; not yet run on a physical Termux device.

## What this adds

`brain_v12/brain/termux_bitcoin_worker.py` is a bounded launcher for a locally installed, trusted cpuminer-compatible executable. It selects Bitcoin's SHA-256d algorithm, requires explicit opt-in, refuses GitHub Actions, requires a Stratum pool and pool worker name, caps the run at five minutes and two CPU threads, and stops at a readable thermal limit.

It does **not** implement hashing itself and does not install/download a miner. The installed binary must support the documented cpuminer CLI options `-a sha256d -o URL -u WORKER -p x -t N`. Verify the binary's source, checksum, architecture compatibility, and TLS behavior before use. The wrapper does not pass private wallet keys; the pool worker name is typically a pool-defined username or wallet.worker string.

## Zero-budget and device safety

- No paid cloud is provisioned and no spend is authorized.
- Phone CPU SHA-256d is not competitive with dedicated Bitcoin ASICs; expect negligible mining output, heat, battery drain, and possible throttling.
- Start with one thread and 60 seconds. Stop if the phone heats up, becomes unstable, or battery drain is unacceptable.
- Use a pool account/worker you control and a pool endpoint that explicitly supports Bitcoin SHA-256d. Do not paste credentials into chat.
- A readable thermal sensor is not guaranteed on Android. If sensors are unavailable, the run is still bounded by duration/thread count, but temperature-based stopping cannot be guaranteed.

## Termux setup

Run from the repository checkout in Termux after Python is installed:

```bash
python -m unittest brain_v12.tests.test_termux_bitcoin_worker -v
```

Set configuration only after installing and verifying a compatible miner:

```bash
export BRAIN_ENABLE_LIVE_MINING=YES
export BRAIN_MINING_POOL_URL='stratum+tcp://YOUR_POOL_HOST:PORT'
export BRAIN_MINING_WORKER='YOUR_POOL_WORKER'
export BRAIN_MINING_THREADS=1
export BRAIN_MINING_DURATION_SECONDS=60
python -m brain_v12.brain.termux_bitcoin_worker
```

Do not use a placeholder host. Replace it with a pool endpoint from the pool you independently chose. The worker's conventional pool password is fixed to `x` to avoid passing a secret in process arguments.

## Evidence interpretation

The launcher prints `PROCESS_STARTED_NOT_POOL_VERIFIED` and later `WORKER_EXITED_REQUIRES_POOL_EVIDENCE`. Neither means that mining succeeded. A real mining gate requires protocol-derived pool authorization, measured hashrate over a stated window, and accepted/rejected/stale share counters. Revenue is a separate gate requiring independent payout and wallet/transaction confirmation. Never infer income from process exit status or simulated ASIC output.
