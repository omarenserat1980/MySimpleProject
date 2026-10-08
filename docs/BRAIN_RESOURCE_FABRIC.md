# Brain Resource Fabric

## Purpose

Brain Resource Fabric is the control-plane abstraction that turns physical or virtual
capacity into composable resources. It does not create physical capacity. Providers
must advertise real or virtual capacity before Brain can allocate it.

## Resource model

Every resource has a stable resource_id, a kind (compute, memory, accelerator, storage,
network, security), provider_id, capacity and unit, capability attributes, and health/state.

A workload expresses intent through ResourceRequest objects rather than hard-coding a
motherboard, CPU model, RAM stick, or disk.

## Lifecycle

DISCOVER -> PLAN -> RESERVE -> COMPOSE -> RUN -> VERIFY -> RELEASE

Reservations have leases. Expired leases are reclaimed. Required requests block composition
when capacity is absent; Brain never fabricates capacity.

## Current implementation

brain_v12/brain/resource_fabric.py provides resource registration and inspection,
capability/attribute matching, deterministic planning, reservation checks, lease expiry,
composition from multiple resource kinds, and explicit release.

This layer is provider-neutral. Next adapters can expose the existing Brain virtual
datacenter/blades, Windows Server 2025 / Hyper-V, QEMU/KVM, CXL memory/accelerator fabrics,
and remote/cloud providers.

## Design boundary

A virtual CPU, virtual RAM, virtual chipset, vTPM, virtual NVMe and virtual NIC are
software-defined representations. They consume host resources. The fabric therefore tracks
capacity and provenance rather than pretending virtual resources are unlimited.

## Safety and control

Reservations are explicit, resource IDs are auditable, required resources cannot silently
degrade into a fake substitute, provider-specific execution remains behind adapters, and
the fabric itself does not execute arbitrary host commands.
