# BRAIN-ASIC-001 — standalone design unit

This directory is the isolated entry point for the single canonical Brain ASIC design instance. It reuses the existing RTL and known-answer lab; it does not fork or silently modify the RTL.

## Run

From the repository root:

```bash
python3 brain_v12/asic/unit_001/run_unit.py
```

Optional evidence output directory:

```bash
BRAIN_ASIC_UNIT_001_OUT=/absolute/path/to/evidence python3 brain_v12/asic/unit_001/run_unit.py
```

The runner invokes the existing `brain_v12/asic/sha256d_lab.py`, records its log and report, then writes `unit-001-report.json`. It does not install tools, contact a pool, access credentials, start mining, or change production settings. Missing Icarus Verilog tools result in a blocked status, not a simulated pass.

## Current design boundary

The RTL currently covers SHA-256 compression, an 80-byte Bitcoin header SHA-256d datapath, target comparison, and bounded nonce sweep. It is a digital RTL design baseline, not yet a complete Stratum client or proof of pool mining. Do not infer ASIC silicon, hashrate, power, accepted shares, payouts, or profit from simulation.

## Exit gates

1. **RTL simulation:** real Icarus Verilog compile/run logs and required pass markers.
2. **Synthesis:** separately generated and inspected netlist and synthesis report.
3. **Physical ASIC:** layout/DRC/LVS, tapeout/foundry evidence, device identity and lab measurements.
4. **Live mining:** authorized pool configuration, accepted-share evidence and independently captured telemetry.
5. **Finance:** independently evidenced payout, measured power and actual costs.

This package is independent in entry point and evidence output, while source RTL remains canonical in `brain_v12/asic/rtl/`. Budget remains JOD 0; paid services, secret changes, deployments and production changes are not authorized.
