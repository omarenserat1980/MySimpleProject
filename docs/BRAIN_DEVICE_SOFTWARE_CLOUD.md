# Brain Device Software Cloud

Status: implemented on branch brain-software-cloud-pool from main.

## Purpose

Electronic Brain can treat the devices it controls as a single software cloud:
the physical laptop and an explicitly enrolled Android executor become cloud nodes,
while Brain provides the control plane, resource discovery, scheduling policy, and
evidence boundary.

This does not create physical CPU/RAM in software and does not create external
cloud resources.

## Node model

- Laptop/host node: measured locally by Brain at runtime.
- Android node: admitted only from the existing authenticated/enrolled Android
  heartbeat and bounded capability adapter.
- Brain: owns the logical pool and chooses a node through the existing
  fail-closed PortableResourceOrchestrator.
- External cloud: not required for this architecture and is not provisioned by
  this feature.

## API

- GET /api/cloud-pool/status — read-only observation of the device-backed pool.
- POST /api/cloud-pool/plan — side-effect-free scheduling decision. A PLANNED
  response means only that a node passed policy; it does not mean the task executed.

## Safety

- Cost is always normalized to USD and forced to zero.
- No paid executor is enabled.
- No arbitrary shell capability is added.
- Stale/un-enrolled Android devices are excluded.
- Physical capacity values are measured/observed; no synthetic capacity is advertised.

## Validation

Run:

PYTHONPATH=. python -m unittest brain_v12.tests.test_device_cloud_pool brain_v12.tests.test_device_bridge_android_capacity brain_v12.tests.test_portable_resource_orchestrator

Runtime status must be checked on a real host and a real enrolled Android device before
claiming that the two-node cloud is live.
