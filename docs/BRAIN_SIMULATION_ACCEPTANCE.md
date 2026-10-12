# Electronic Brain Simulation-First Acceptance

## Purpose

The simulation lab is the first validation layer for Electronic Brain. It runs the Arkan device twin, sandboxed PowerShell emulator, Digital Twin snapshot checks, failure injection/recovery, and the Golden Closed Loop without requiring an online device, Hyper-V, KVM, a cloud VM, or paid infrastructure.

## Run locally

From the repository root:

```bash
python tools/brain_simulation_acceptance.py --output artifacts/brain-simulation-acceptance.json
PYTHONPATH=. python -m unittest \
  brain_v12.tests.test_digital_twin_fabric \
  brain_v12.tests.test_arkan_device_emulator \
  brain_v12.tests.test_arkan_twin_golden_loop \
  brain_v12.tests.test_powershell_emulator \
  brain_v12.tests.test_desktop_commander_emulator -v
```

The runner creates a temporary sandbox and removes it on exit. Its JSON report identifies each check, status, duration, and SIMULATED provenance.

## What PASS means

A passing simulation report means that the tested emulator behaviors, evidence integrity, recovery path, and simulation/real boundary worked in the test process. It does **not** prove that Windows Server 2025 booted, that Azure resources exist, or that RDP works from ASUS/Arkan.

The suite must never promote simulated evidence into real evidence. A real boot acceptance requires independent evidence from the actual guest disk/boot process in the same authorized execution, followed by an interactive RDP sign-in from the ASUS client.

## CI

The Brain Simulation Acceptance Suite workflow runs on pull requests touching the emulator contracts and can be launched manually. It uploads a 30-day artifact including evidence generated before a later test failure.

## Resource policy

This path uses GitHub-hosted CI and temporary local directories only. It does not provision cloud resources, start local VMs, contact physical devices, read secret values, or install paid dependencies. Real-world actions remain separately gated.
