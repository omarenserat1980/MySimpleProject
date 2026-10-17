# Brain Linux Simulator (simulation-only)

## Purpose

The Linux Simulator provides a deterministic, no-side-effect profile check for Brain planning and tests. It is not a Linux kernel, container, VM, or real host preflight. It must never be used as proof that Arkan has Linux x86-64, sufficient physical/effective memory, disk headroom, /dev/kvm, QEMU, or UEFI firmware.

## Run tests

From the repository root:

    python -m unittest brain_v12.tests.test_linux_simulator -v

The API is brain_v12.brain.linux_simulator.evaluate_linux_simulation(profile). The result uses simulation_status=SIMULATION_PASS or SIMULATION_BLOCKED; it does not return a real-host READY status.

## Truth and safety boundaries

Every result explicitly sets fidelity=SIMULATED, host_capacity_verified=false, native_linux_running=false, qemu_started=false, kvm_access_verified=false, resources_allocated=false, real_execution_authorized=false, and windows_boot_verified=false.

Profile fields such as qemu_expected and kvm_expected are hypothetical inputs for scenario testing only. They are not probed facts.

## Real execution remains separate

The existing brain_v12/tools/arkan_windows_server_2025_preflight.py remains the fail-closed real-host gate. The .github/workflows/brain-windows-real-boot.yml workflow must continue to require the protected execution contract, trusted executor attestation, actual Linux x86-64 capacity, readable/writable KVM, QEMU/UEFI tools, trusted installation media, and independent guest boot evidence. A simulation pass cannot satisfy or bypass any of those checks.

This change creates no VM, does not install packages, does not download ISO media, does not enable networking, and does not modify the Windows real-boot workflow.
