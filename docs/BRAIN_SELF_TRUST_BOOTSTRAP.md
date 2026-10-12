# Brain Self-Trust Bootstrap

## Purpose

The first Brain self-test must not depend on the general control-plane secret.
A newly booted Brain must be able to establish local execution trust using the
registered device Agent Key without granting the device Control Plane authority.

## Bootstrap chain

BOOT
-> Brain Runtime
-> Local Trust Root (Agent Key file)
-> Device Bridge enabled
-> One-shot self-test capability
-> Agent claims task
-> Agent executes allowlisted self-test
-> Agent reports evidence
-> Brain verification gate
-> BRAIN READY

## Security boundaries

- BRAIN_CONTROL_KEY is not required for bootstrap self-test.
- Agent Key and Control Key remain separate security domains.
- The bootstrap endpoint accepts only brain_self_test.
- The task remains allowlisted by DeviceBridge.ALLOWED_TASKS.
- The bootstrap capability is scoped to the authenticated device agent.
- Verification is based on actual unittest evidence (returncode == 0,
  Ran ... and OK in combined stdout/stderr).
- Missing local Trust Root keeps the Device Bridge disabled.
- Cloud deployments may explicitly disable the bridge with
  BRAIN_ENABLE_DEVICE_BRIDGE=0.

## Proven proof

Device: arkan-industrial-01

Final proof sequence:

SELF_TEST_REQUESTED -> CLAIMED -> REPORTED ok=True -> VERIFIED verified=True

Final self-test evidence:

- return code: 0
- tests executed: 18
- unittest result: OK

This contract is the bootstrap foundation for the future Brain-owned ISO:
the ISO may create/register its local Trust Root during first boot, then perform
the same bounded self-test before declaring the system ready.
