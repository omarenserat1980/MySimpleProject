# BRAIN Android Habitat — Gate Specification

## Purpose

Turn an Android/Termux device into a Brain-managed execution habitat while preserving Android's security model.

## Existing bridge

The repository already contains:

- brain_emulator_agent/v12_agent.py
- V12 agent identity/key configuration
- heartbeat
- task polling
- task reporting
- allowlisted execution

Habitat v1 must extend this bridge rather than replace it.

## Readiness sequence

1. IDENTITY — V12_AGENT_ID exists and the existing key contract is available.
2. CONNECTIVITY — V12_BRAIN_URL/BRAIN_URL is configured and Brain readiness is reachable.
3. RUNTIME — Python is available and platform information is captured.
4. STORAGE — Brain habitat directory is writable.
5. PERMISSIONS — user-space only; no root escalation or bootloader manipulation.
6. SELF-TEST — Habitat checks execute successfully; existing Brain self-tests remain authoritative.
7. READY — only when every gate passes.

## Failure rule

A failed gate produces BLOCKED and must not be converted into READY by an error-tolerant workflow.

## Recovery rule

Next layers: offline queue, restart recovery, heartbeat recovery, policy/permission decisions, resource health, and self-healing.

## Ownership boundary

Brain-owned means Brain controls its software workspace, tasks, policies, telemetry and lifecycle. It does not bypass Android, OEM, carrier or user security controls.

## Target progression

HABITAT V1 -> HABITAT MANAGER -> SELF-HEALING -> SYSTEM INTEGRATION -> OPTIONAL BRAIN ANDROID IMAGE/ROM
