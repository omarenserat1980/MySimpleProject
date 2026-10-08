# Brain Cloud Machine v1

The cloud machine is the primary Brain execution substrate.

## Gate order

1. Cloud Machine Acceptance
2. Host runtime / virtualization verification
3. Windows Server 2025 media verification
4. VM disk and UEFI preparation
5. Windows installation/boot
6. Guest evidence
7. Brain Executor registration
8. Production readiness

A later gate cannot imply an earlier gate.

## Runtime topology

Cloud host -> KVM/QEMU -> Windows Server 2025 -> Brain Executor -> Brain Control Plane.

Arkan remains a recovery executor. Termux remains an emergency/device executor.

## Authority

The Windows closed-loop gate remains fail-closed and requires an externally
issued, signed execution contract. This document does not create authority and
must never be used to bypass BRAIN_AUTHORITY_SIGNING_TOKEN.

## Resource baseline

The initial acceptance baseline is x86_64/AMD64, >=2 vCPU, >=4 GiB RAM,
>=80 GiB storage, networking, virtualization, UEFI, QEMU and OVMF.

Production sizing may exceed this baseline; the baseline is only the minimum
needed to enter the Windows verification pipeline.

## Operating principle

ChatGPT proposes. Brain decides. An authorized executor acts. Evidence proves.
Brain commits the resulting state only after verification.
