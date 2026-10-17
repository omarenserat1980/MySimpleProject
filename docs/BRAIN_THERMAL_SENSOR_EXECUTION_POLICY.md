# Brain Thermal Sensor Execution Policy

## Decision

**Thermal Sensor = Optional for Cloud Simulation / Required when mandated for Real Hardware Safety.**

- CLOUD_SIMULATION: a physical sensor is not a prerequisite. Brain may use the existing software thermal model, but outputs must remain explicitly estimated and evidence must be classified as SIMULATION.
- REAL_HARDWARE: when the applicable hardware, operational, or safety policy mandates a sensor, missing or invalid sensor telemetry blocks the operation.
- A real-hardware alternative is accepted only when an applicable safety policy explicitly authorizes it and the caller supplies approved_alternative=True. This flag is a policy assertion, not automatic proof; production integration must bind it to verifiable approval evidence.
- If execution mode is absent or unknown, the gate fails closed.
- This policy helper does not probe a device, start workloads, enable mining, or prove physical safety. It must be called by the relevant real-hardware execution path before launch.

## Implementation

brain_v12/virtual_hardware/thermal_safety_policy.py provides a pure, deterministic policy function. It does not change the existing PowerThermalModel, whose temperatures remain estimates and are never treated as physical measurements.

## Verification

Run:

python -m unittest brain_v12.tests.test_thermal_safety_policy -v

Tests cover sensor-free cloud simulation, valid and invalid physical readings, explicit alternative approval, unknown execution modes, and evidence classification.
