# Brain Virtual Server Fabric

## Scope

The first server-fabric increment provides deterministic server workload profiles, host-capacity observation, backend capability discovery, and fail-closed resource admission. It is an additive layer under `brain_v12/virtual_hardware/`; it does not introduce a new orchestrator or start VMs.

## Current implementation

- `server_fabric.py` defines declarative server profiles for general, web, database, file, API, monitoring, backup, DNS, DHCP, directory, certificate, and reverse-proxy workflows.
- `observe_host_capacity()` observes logical CPU count, available memory where the host exposes it, free disk bytes, operating system, and architecture. Host observations are not reservations.
- `discover_backends()` detects selected executables and platform indicators for QEMU, KVM, Hyper-V, libvirt, Docker, and Podman. Presence detection is not proof that a backend can boot a guest.
- `admit_server_workload()` checks a profile against observed capacity and safety reserves. It does not reserve resources or start a VM.
- `validate_server_release()` recognizes Windows Server 2025 as a target identifier without claiming media, licensing, installation, or boot verification. A requested 2023 label is rejected as unverified pending authoritative product/media confirmation.

## Fidelity labels

- `SIMULATED`: deterministic model only.
- `ESTIMATED`: approximation calculated from a declared model.
- `HOST_OBSERVED`: a measurement read from the current host.
- `GUEST_VERIFIED`: evidence collected from a running guest.
- `PHYSICALLY_CALIBRATED`: measurements compared with the relevant physical system.

Virtual profile capacity is not host capacity. Admission returns `ADMITTED_FOR_PLANNING`, not an execution or reservation claim. Native guest execution, network isolation, snapshots, and recovery require backend-specific implementation and evidence in later increments.

## Verification

Run:

```sh
python -m unittest brain_v12.tests.test_virtual_server_fabric -v
```

The focused tests verify profile determinism, Windows release labeling, host provenance, fail-closed admission, and non-provisioning backend discovery.
