# System Inventory — Base Expansion V2

## Repository layers observed

### Existing Brain
- brain_v12/brain: cognition, orchestration, memory, decisions, tasks, supervisors, permissions, evidence, execution, security, sync and integrations.
- brain_v12/business: commercial, opportunity, game, revenue and economics capabilities.
- brain_v12/ai_fabric: AI provider/fabric capabilities.
- brain_v12/brain_git: Brain-owned Git service concepts.

### Existing execution and interfaces
- brain_v12/app.py
- brain_v12/brain_ffmpeg.py
- brain_v12/ci/
- .github/workflows/
- tools/brain_emulator_agent.py
- termux_agent/
- v12-agent/

### Existing verification
- verification/latest.json
- tests/
- extensive package-level test modules

## New foundation boundary
The independent foundation will live under platform_foundation/ and MUST NOT import brain_v12 in its base layer.

## Integration boundary
Brain integration will occur only after PLATFORM_STATUS=VERIFIED or VERIFIED_WITH_KNOWN_GAPS with all critical gaps closed.
