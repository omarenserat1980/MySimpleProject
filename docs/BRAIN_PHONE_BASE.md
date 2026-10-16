# Brain Phone Base — simulation first

## Goal
Treat authorized phones as potential Brain resource nodes, but do not count a
phone as real capacity until its identity, authenticated connection, resources,
consent, and secure transport are verified. This implementation starts in
simulation mode and is zero-cost-first.

## Current implementation
Run from the repository root:

```bash
python -m brain_v12.tools.brain_phone_base
python -m unittest brain_v12.tests.test_brain_phone_base -v
```

The default command prints a synthetic phone profile. Its CPU, memory, storage,
network, and battery values are fixtures, not measurements from a real phone.
It performs no network calls and does not register a real device, dispatch work,
start mining, or claim revenue.

To evaluate a local evidence JSON file without activating a device:

```bash
python -m brain_v12.tools.brain_phone_base --evidence-json ./phone-evidence.json
```

The gate fails closed unless all five evidence categories contain a verified
flag, trusted source, and digest: device registration, authenticated heartbeat,
independent resource attestation, user consent, and secure transport. Even if
the shape passes, the result is only `ELIGIBLE_FOR_MANUAL_REVIEW`; this code
does not validate the evidence cryptographically and never activates a device.

## Real-device rollout gates
1. **Simulation:** tests pass and synthetic metrics remain clearly marked.
2. **Local measurement:** run the existing `brain_v12.tools.brain_live_resource_agent`
   on the phone; retain its self-reported status as unverified capacity.
3. **Authenticated connection:** Brain API and device bridge are configured;
   send one opt-in heartbeat using a per-agent key held only in local environment
   variables or a secret manager. HTTPS is required for remote Brain URLs.
4. **Independent verification:** trusted server-side records verify the device
   identity, recent heartbeat, resource evidence, consent, and transport.
5. **Manual activation review:** require explicit approval before any real task
   is dispatched. This release does not implement activation or arbitrary task
   execution.

## Evidence boundary
- Unit tests prove code behavior in CI, not that a phone is online.
- A heartbeat acknowledgment proves an authenticated connection at that time,
  not independent hardware backing or usable capacity.
- Phone battery/thermal state and user consent must be checked before future
  workload scheduling. No always-on behavior is enabled here.
- No mining, payments, revenue, paid cloud provisioning, or secret collection.
