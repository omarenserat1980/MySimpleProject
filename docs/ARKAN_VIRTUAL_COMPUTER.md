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


## Windows Server 2025 real guest: admission gate

The canonical Arkan identity is a software identity; it is not a hypervisor. A real Windows kernel must run on an authorized execution host with QEMU/KVM, UEFI firmware, available CPU/RAM/disk, legitimate Microsoft installation media, and the short-lived signed Brain execution contract.

Before downloading installation media, the real-boot workflow runs `brain_v12/tools/arkan_windows_server_2025_preflight.py`. It fails closed unless all of these checks pass:

- Canonical identity is exactly `arkan-virtual-01`.
- Host is Linux x86-64 with at least 2 logical CPUs, 4 GiB total RAM, and 3 GiB currently available RAM.
- At least 25 GiB of workspace disk space is free.
- `/dev/kvm` is readable/writable; QEMU, qemu-img, OVMF, and ISO/WIM/FAT utilities are present.
- The signed execution-contract gate has already verified the current run's contract.

The gate is read-only. It does not download media, create a disk, start QEMU, or mark Windows as booted. It writes `arkan-windows-server-2025-readiness.json` into the run evidence. A ready result means only that an authorized boot attempt may proceed; acceptance still requires guest-generated evidence and the independent completion/proof gates.

Run locally on an eligible, authorized runner after contract verification:

```bash
python3 brain_v12/tools/arkan_windows_server_2025_preflight.py \
  --workspace "$PWD" \
  --contract-gate windows-execution-contract-gate.json \
  --output arkan-windows-server-2025-readiness.json
python3 -m unittest brain_v12.tests.test_arkan_windows_server_2025_preflight -v
```

A modeled 128-vCPU/1-TiB profile does not satisfy these host checks. The previously constrained ASUS host (about 3.6 GiB total RAM) does not meet the new minimum and must not be silently used as the execution backend. Use a separately authorized, adequately sized execution host; no paid cloud resource is provisioned by this change.


## Durable simulator checkpoints

Authenticated endpoints are available while Brain is running:

- `POST /api/virtual-hardware/arkan/checkpoint` — persist the canonical simulator's CPU, modeled RAM, virtual storage, NIC queues, GPU framebuffer, bus counters, and thermal model snapshot.
- `POST /api/virtual-hardware/arkan/restore` — verify the saved checkpoint, restore supported simulator state, and re-run virtual firmware.

The default checkpoint file is `~/.brain/virtual-machines/arkan-virtual-01.checkpoint.json`; override it with `BRAIN_ARKAN_CHECKPOINT_PATH`. Writes use atomic replacement, best-effort restrictive file permissions, and an envelope checksum in addition to the simulator checkpoint checksum. These endpoints require the existing Brain control key.

Restore intentionally reports that kernel process tables/open handles are not restored. A simulator checkpoint is not a native Windows VM disk, and it never proves Windows Server 2025 boot. Back up the checkpoint file separately if you need off-device disaster recovery.
