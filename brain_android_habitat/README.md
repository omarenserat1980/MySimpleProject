# BRAIN Android Habitat

BRAIN Android Habitat is the Brain-owned runtime layer for an Android/Termux node.

## Contract

The habitat does not bypass Android security or claim OEM/system ownership. It provides a Brain-controlled operational boundary:

IDENTITY -> CONNECTIVITY -> RUNTIME -> STORAGE -> PERMISSIONS -> SELF-TEST -> READY

A node is **READY** only when every gate passes.

## Environment

- BRAIN_URL / V12_BRAIN_URL
- V12_AGENT_ID
- V12_AGENT_KEY_FILE or V12_AGENT_KEY
- V12_POLL_SECONDS

The existing `brain_emulator_agent/v12_agent.py` remains the execution bridge.

## Next layers

1. Habitat Manager
2. Offline queue and recovery
3. Permission/policy gate
4. Health and resource telemetry
5. Self-healing
6. Optional Android system/ROM integration
