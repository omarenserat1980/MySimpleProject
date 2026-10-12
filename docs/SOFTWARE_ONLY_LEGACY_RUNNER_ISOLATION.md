# Software-only execution and legacy real-boot isolation

## Required Brain execution

Electronic Brain's default execution path must use software workers and GitHub-hosted execution where bounded cloud execution is needed. It must not require Arkan, user-owned PCs, Android/Termux, Hyper-V, QEMU/KVM, or self-hosted hardware runners to initialize, test, or route ordinary Brain workloads. Virtual CPU, RAM, disk, power, and thermal values are modeled values unless independently calibrated.

## Windows Server 2025 real-boot workflow

`.github/workflows/brain-windows-real-boot.yml` is a **manual, optional evidence workflow** for a distinct objective: proving a real Windows Server 2025 guest booted under QEMU on a specially provisioned, trusted runner. It is not a simulation and it is not part of the normal software-node execution contract.

That workflow deliberately requires a protected GitHub Environment, a dedicated runner with the labels in its `runs-on` selector, QEMU/OVMF tooling, and protected credentials. If those resources are absent, the real-boot proof is unavailable; this must not block the default Brain software-only path or be worked around by weakening its security gates.

Do not dispatch this workflow as a substitute for virtual-server profile tests. A passing unit-test or profile workflow does not prove Windows boot. Conversely, a missing real-boot runner does not mean the software-only Brain core is unhealthy.

## Handling older runner setup instructions

Documents and scripts for configuring Arkan, WSL, internal runners, Hyper-V, or QEMU may be retained as historical/manual diagnostics. They must be clearly described as optional legacy material, not as steps required to run Brain. Do not register physical devices as execution workers, and do not restore a self-hosted runner as a required status check or core runtime dependency.

Before promoting a change from draft, audit workflow `runs-on` selectors and branch-protection/status-check settings separately. Classify each workflow as:
- **Core software-only CI:** must run without user-owned hosts or self-hosted runners.
- **Optional real-boot proof:** manual, separately protected, and allowed to remain unavailable without blocking core CI.
- **Legacy/manual diagnostic:** not part of the core release gate.

## Evidence language

Use distinct claims:
- `SIMULATED`: modeled configuration or deterministic simulation.
- `HOST_OBSERVED`: measurement of the current host.
- `GUEST_VERIFIED`: evidence from an actually running guest.
- `PHYSICALLY_CALIBRATED`: measurements compared against the relevant physical system.

Never report simulated 128 vCPU, 1 TiB RAM, or 100 TiB virtual disk as allocated resources. Never report Windows Server 2025 as booted unless the independent guest evidence gate passes.
