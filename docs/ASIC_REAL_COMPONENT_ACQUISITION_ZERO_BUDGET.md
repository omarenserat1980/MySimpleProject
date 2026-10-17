# BRAIN-ASIC-001 — Real Component Acquisition Plan (Zero Budget)

**Status:** OPEN / NO PHYSICAL PARTS VERIFIED  
**Budget ceiling:** 0 JOD unless the owner explicitly authorizes a change  
**Procurement rule:** Do not place orders, make payments, contact sellers on the owner's behalf, or claim possession without explicit authorization and evidence.

## Goal
Obtain at least one real, identifiable SHA-256 Bitcoin-mining ASIC component and a compatible way to control/test it, without treating simulated catalog entries as physical inventory.

## Preferred path: donated or salvaged working hashboard
1. Ask for a donated, discarded, or repair-parts hashboard from an Antminer S19j Pro/S19j Pro+ repair shop, electronics recycler, maker group, or mining operator.
2. Prefer an intact board with legible board revision, photos of both sides, and known origin. A whole hashboard is more useful than a loose chip because it includes the supporting power, clock, reset, and chain circuitry.
3. Do not assume every BM1362 suffix is compatible. The public emberOne/00 reference specifically lists BM1362AA/AB/AC/AD as candidates and says AI/BD are untested and AJ/AK incompatible with that design. Confirm the exact revision against the selected board/design before use.
4. Request a no-cost donation or a board offered for recycling; do not promise payment or shipping reimbursement. If shipping is not free, stop and report that the zero-budget gate is blocked.

## Alternative path: free, low-risk real components first
If no ASIC hashboard can be obtained for free, request donated generic components for a non-powered inventory/measurement kit (controller board, thermal sensor, fan, connectors, passive parts). These are real components but **do not constitute a mining ASIC** and must not be counted as one.

## Verification required before adding to physical inventory
For every received item, record:
- Evidence ID and date received
- Clear photos of labels/markings and both board sides
- Manufacturer/model/board revision as printed (unknown remains null)
- Donor/source statement, with personal details omitted from public artifacts
- Physical serial number only if present on the item; never invent one
- Continuity/visual inspection results; any powered test requires a reviewed safe procedure
- Evidence class = `PHYSICAL_OBSERVED` only when supported by actual photos/inspection; test outcomes must be separately recorded

Internal Brain simulation IDs (e.g. `BRAIN-ASIC-001-U1`) identify catalog entries only. They are not manufacturer serial numbers and do not prove ownership, manufacture, or possession.

## Public reference design
The 256 Foundation emberOne/00 is an open-source 12-chip BM1362 hashboard design, approximately 100 W class, requiring a separate USB control board. Its design files are a reference, not a verified Brain design and not a promise of zero-cost fabrication:
- https://github.com/256foundation/emberone00-pcb
- https://github.com/256foundation/mujina
- https://mujina.org/reference/hardware-compatibility

## Gates
- `G0_SOURCE_IDENTIFIED`: a donor/source is identified, not yet acquired.
- `G1_PART_RECEIVED`: physical item and evidence received.
- `G2_IDENTITY_VERIFIED`: exact markings/revision documented; compatibility checked.
- `G3_SAFE_TEST_PLAN`: electrical limits and test method reviewed before power-on.
- `G4_CONTROL_AND_HASH_TEST`: only pass with captured device telemetry and reproducible test evidence.
- `G5_POOL_ACCEPTANCE`: only pass with independently verifiable accepted shares from a real pool session.
- Fabrication, assembly, hashrate, revenue, and mining are never inferred from simulation or CI success.

## Current truthful state
- Physical ASIC chips received: 0 verified
- Physical hashboards received: 0 verified
- Free donor confirmed: no
- Purchases authorized: no
- Budget: 0 JOD
- Assembly readiness: false
- Live mining evidence: none
