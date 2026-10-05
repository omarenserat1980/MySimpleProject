# Brain Device Agent — Open-Source Research Integration

## Objective
Solve the runtime connection problem without making GitHub Actions the runtime authority.

## Relevant open-source designs
- Taiwan: Agenvoy is a Taiwan-developed self-hosted AI agent harness with a long-lived local daemon, outbound integrations, scheduling, tool routing and sandbox boundaries.
- China: Poiesis describes a persistent autonomous-agent OS with scheduler, process state, watchdog/heartbeat, supervision and gated evolution with rollback.
- Android/Termux: open-source watchdog projects demonstrate wake-lock, Termux:Boot and boot-time restart as necessary persistence mechanisms on modern Android.
- Termux agent management: open-source Termux agent managers demonstrate heartbeat dashboards, crash detection, auto-restart and wake-lock/boot patterns.

## Geographic search honesty
Searches were also performed for India and Bangladesh. No sufficiently strong, clearly attributable India- or Bangladesh-origin implementation was found that should be treated as a design authority for this exact problem. Brain therefore does not invent attribution or equate geography with quality.

## Brain integration
1. Outbound-only Agent; no public listener on the device.
2. Heartbeat is the online proof.
3. Existing DeviceBridge remains the authority.
4. Agent reconnects with exponential backoff.
5. Existing allowlist remains the execution boundary.
6. Termux:Boot and wake-lock are explicit persistence layers.
7. Guardian supervises the local executor separately from the network Agent.
8. GitHub remains source/evidence, not runtime authority.
9. ONLINE/AUTONOMOUS claims require fresh heartbeat and execution evidence.

## Acceptance
Installing the program is not proof of connectivity. DeviceBridge must observe a fresh heartbeat within TERMUX_AGENT_TTL_SECONDS.
