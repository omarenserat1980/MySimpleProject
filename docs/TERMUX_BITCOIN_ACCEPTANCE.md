# Termux Bitcoin SHA-256d Acceptance Test

This is a staged acceptance procedure for Electronic Brain. It does not claim mining, pool connectivity, accepted shares, or revenue until each gate has independent evidence.

## 1. Prepare Termux

Run on the Android device in Termux:

```bash
pkg update
pkg install python git clang make -y
```

Make sure the repository exists locally. If it is already cloned elsewhere, use that path rather than cloning a second copy:

```bash
cd ~/MySimpleProject
git status --short
git branch --show-current
```

The worker and acceptance script must be on the current branch. Do not switch branches or discard local changes without checking `git status` first.

## 2. Run the non-mining preflight

```bash
bash brain_v12/tools/termux_bitcoin_acceptance.sh
```

The script is deliberately safe by default. It does not start a miner or connect to a pool. It records device architecture, available build tools, repository revision, worker unit tests, and whether a `cpuminer` executable is present. Its report is saved under `~/brain-mining-evidence/`.

If the repository is not at `~/MySimpleProject`, set the actual local path first:

```bash
export BRAIN_REPO_ROOT="/actual/path/to/MySimpleProject"
bash "$BRAIN_REPO_ROOT/brain_v12/tools/termux_bitcoin_acceptance.sh"
```

## 3. Gate on compatibility before building or running a miner

Record `uname -m` and `getprop ro.product.cpu.abilist`. Select a reputable, auditable miner release or source that explicitly supports the device ABI and Android/Termux environment and supports Bitcoin SHA-256d over Stratum. Do not assume a Linux x86-64 binary will work on Android ARM, and do not install an arbitrary executable from an untrusted mirror.

Verify the downloaded binary's provenance/checksum against the publisher's official release. Check its help/version output for SHA-256d and Stratum support. If support cannot be verified, stop at this gate.

## 4. Live pool test (separate, explicit approval required)

Only after the binary and pool are verified, configure the worker using the miner's documented arguments. Keep passwords, API keys, and wallet secrets out of shell history, screenshots, evidence logs, and Git commits. Use a short, low-thread test with the device cool and on a stable connection; stop if temperature rises, the device becomes unstable, or battery/thermal warnings occur.

Do not run a live miner in GitHub Actions or other CI. A successful process exit or a miner's own text output is not enough to prove pool acceptance.

## 5. Required evidence gates

- **Local test:** command, branch/commit, test output, ABI, binary version and verified checksum.
- **Pool session:** session/worker visible in the pool's authenticated dashboard or API.
- **Hashrate:** pool-side measured hashrate over an adequate averaging window.
- **Shares:** pool-side accepted, rejected and stale counters. Record the observation time and worker identity without exposing secrets.
- **Revenue:** an independently verifiable payout/transaction record. Shares or estimated earnings alone are not a completed payout.

Until all applicable evidence is collected, report the status as `NOT VERIFIED`. Never infer physical ASIC hardware or profitable mining from a CPU worker running on a phone.
