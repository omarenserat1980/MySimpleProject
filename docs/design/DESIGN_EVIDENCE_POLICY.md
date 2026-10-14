# Design Evidence Policy

## Evidence levels
- PLANNED: proposal only.
- DESIGNED: reviewed design/specification exists.
- IMPLEMENTED: implementation files exist.
- SIMULATED: a named simulator ran with recorded inputs and outputs.
- TESTED: a defined test command ran and its result is captured.
- VERIFIED: relevant independent check/review supports the specific claim.
- HARDWARE_VERIFIED: physical-device evidence supports the claim.
- MANUFACTURED_VERIFIED: credible physical manufacturing evidence exists.
- REVENUE_VERIFIED: reconciled financial/provider evidence supports realized revenue.
- BLOCKED: prerequisite/tool/permission is missing.
- FAILED: a required check ran and failed.

## Rules
1. Evidence must name the claim it supports.
2. Evidence must identify source, timestamp, commit/version, command/tool, result, and artifact/checksum where relevant.
3. Simulation evidence must carry a simulation marker and must not satisfy real-device gates.
4. A skipped or unavailable test is BLOCKED, not PASS.
5. Self-reported status without supporting evidence is not independent verification.
6. No physical manufacture, live mining, accepted shares, or revenue claim from source files or CI status alone.
7. Keep secrets and sensitive values out of artifacts.
