# Arkan Canonical Virtual Computer

## Identity

- Display name: `Arkan`
- Canonical ID: `arkan-virtual-01`
- Type: software-defined virtual computer
- Backend: `brain-simulator`
- Readiness after provisioning: `SIMULATION_READY`

The logical identity is independent of a physical ASUS VivoBook, Desktop Commander, a self-hosted runner, or any other host. Host/backend availability and guest execution are separate concerns.

## Brain fleet integration

The fleet inventory uses `arkan-virtual-01` as the canonical Arkan identity and labels its platform `brain-simulator`. The former physical ASUS VivoBook is not an alias for this identity. Fleet status reports `SIMULATION_READY` only when the in-process simulator is booted and a bounded symbolic CPU task has passed; otherwise it reports `NOT_PROVISIONED`, `CONFIGURED_NOT_RUNNING`, or `DEGRADED`. This readiness is limited to symbolic simulation and never proves a native OS boot.

The optional physical host, if configured later, must use a distinct ID such as `arkan-host-asus-vivobook` and cannot inherit Arkan identity.

## API

Both endpoints require the existing Brain control key:

- `POST /api/virtual-hardware/arkan/provision` — reconcile the canonical identity, validate the existing VirtualComputer implementation, boot the simulator, and persist an identity/configuration record.
- `GET /api/virtual-hardware/arkan/status` — read the persisted record without pretending that a simulator is loaded in memory or that a native OS is running.

The registry path defaults to `~/.brain/virtual-machines/arkan-virtual-01.json`. Set `BRAIN_ARKAN_REGISTRY_PATH` to override it. Writes use a same-directory temporary file and atomic replacement.

## What is persisted

The registry stores canonical identity, configuration fingerprint, hardware manifest, last observed simulator status, OS target declaration, and honest readiness/boot claims. The current increment does **not** serialize live RAM/CPU state or provide a persistent native guest disk. Runtime state is explicitly marked as not persisted.

## Hardware and OS fidelity

Virtual CPU/RAM/storage/network/device models remain software models. Configured virtual capacities are not physical host capacity and do not allocate equivalent host resources. External networking defaults to disabled.

Windows Server 2025 is a requested target only. This increment does not download installation media, verify licensing, provision Hyper-V/QEMU, install Windows, or boot a native Windows kernel. The registry must therefore retain `installation_status=NOT_INSTALLED`, `boot_status=NOT_VERIFIED`, and `native_os_boot_verified=false`.

## Verification

Run:

```bash
python -m unittest brain_v12.tests.test_arkan_provisioner -v
python -m py_compile brain_v12/virtual_hardware/arkan_provisioner.py brain_v12/virtual_hardware/api.py
```

A passing simulator test establishes software simulation readiness only, not native guest OS boot. Fleet integration tests also verify that an ASUS/physical host ID cannot be marked as the canonical Arkan identity.
