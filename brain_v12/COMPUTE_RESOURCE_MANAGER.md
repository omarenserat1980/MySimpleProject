# Brain Compute Resource Manager

The read-only compute inventory lives in `brain_v12/brain/compute_resource_manager.py`.

## Run

```bash
python -m brain_v12.brain.compute_resource_manager
python -m brain_v12.brain.compute_resource_manager --hashes 100000 --seconds 5
```

It reports visible CPU capacity, a best-effort available-memory estimate, runtime kind
(including Android Termux and ephemeral GitHub Actions), and a bounded local compute
budget. The report does not start a hash job by itself. The separate bounded compute
runner must be invoked explicitly when a local offline test is wanted.

## Safety and evidence boundary

- The inventory is read-only: no network calls, subprocesses, secret reads, or mining.
- Budgets are clamped to 10,000,000 hashes and 30 seconds.
- CPU/RAM observations are not host attestation, ASIC hash rate, or proof of a persistent executor.
- Live mining, pool submission, pool acceptance, payout, and revenue remain blocked.
- GitHub Actions are classified as ephemeral CI, not 24/7 mining infrastructure.
- The output refuses to overwrite an existing report file.
