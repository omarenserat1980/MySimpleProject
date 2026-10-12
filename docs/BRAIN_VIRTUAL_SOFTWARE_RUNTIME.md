# Electronic Brain Virtual Software Runtime v1

## Objective
Give Electronic Brain a software-defined application layer that can model the workflows of familiar real-world software classes on Brain-owned virtual machines. The virtual hardware and application layers should work without requiring Arkan, a physical Android device, or a paid cloud runtime.

## Architecture

```text
Brain Control Plane
  -> Virtual Datacenter / Blade Scheduler
    -> VirtualComputer (CPU, RAM, bus, storage, NIC, GPU, firmware, kernel model)
      -> VirtualSoftwareRuntime
        -> declarative application profile
          -> bounded lifecycle and approved workflow actions
            -> event evidence / deterministic payload hashes
```

## First supported application classes
- Browser workflow: navigation state, tabs, storage and request/response fixtures.
- Office workflow: document, spreadsheet, presentation and import/export workflow models.
- Database workflow: schema, query fixtures, transactions and connection accounting.
- Media workflow: assets, timeline, render queue and export manifests.
- Developer tools: project inventory, build graph, test fixtures and artifact hashes.
- Network service: virtual endpoints, routing fixtures, simulated latency/loss and health.

## Reality and fidelity contract
- A profile is a deterministic workflow model, **not** a claim that proprietary browser/office/media binaries run.
- Arbitrary Python, shell, native binaries, network access and external side effects are not executed by this runtime.
- Each profile declares simulated behaviors, required capabilities, resource estimates and unsupported behaviors.
- `SIMULATED` is not `VERIFIED`, `PROVISIONED`, or `RUNNING` on physical hardware.
- Virtual CPU/RAM/storage/network capacity is logical accounting. It does not create physical resources or imply native workload performance.
- A real implementation may be attached later through an explicit, permissioned adapter (for example, a QEMU guest or a host application runner); the software-only path remains independent.
- Runtime registry is currently process-local; durable persistence and API integration are follow-up work and must have tests before being called complete.

## Tests
Run from repository root:
`python -m unittest brain_v12.tests.test_virtual_software_runtime -v`

## Next integration gates
1. Verify this module and tests in CI.
2. Integrate the runtime into the existing virtual-computer control plane without creating a second orchestrator.
3. Add authenticated API endpoints and durable checkpointing.
4. Add guest-OS/application adapters with capability gates and independent evidence.
5. Keep native execution, physical bindings, and external network access disabled by default.
