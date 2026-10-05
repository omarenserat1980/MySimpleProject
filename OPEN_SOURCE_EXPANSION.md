# Open Source Expansion Policy

Electronic Brain uses an **Open Source First** policy to reduce vendor lock-in, preserve self-hosting, and improve resilience.

## Candidate stack

| Region | Project | Brain capability | License / status |
|---|---|---|---|
| Global | LangGraph | Stateful agent graphs and orchestration patterns | Evaluate upstream license/version before adoption |
| Global | Kestra | Event-driven workflow orchestration | Open-source project; verify exact component licenses |
| China | Qwen-Agent | Tool use, planning, RAG, code execution and MCP patterns | Apache-2.0 |
| China | AgentScope | Multi-agent teams, pipelines, SOPs, A2A and model routing | Apache-2.0 |
| China | AgentScope Runtime | Sandboxing, agent runtime, APIs and observability | Apache-2.0 |
| China | MS-Agent / ModelScope | Long-running agents, memory, scheduling and research workflows | Apache-2.0 |
| India | AI4Bharat IndicTrans2 | Indian-language translation | MIT for model checkpoints; datasets have separate licenses |

## Adoption gate

No external project becomes a Brain dependency merely because it is popular. Every candidate must pass:

1. license compatibility;
2. pinned/reproducible version;
3. security review;
4. self-hosted/offline feasibility where required;
5. no hidden external-runner dependency;
6. Brain permission and authority enforcement;
7. durable state/checkpoint compatibility;
8. audit/evidence integration;
9. failure, retry and recovery tests;
10. documented removal path.

## Architecture rule

Brain remains the authority for execution, permissions, durable state, checkpoints, verification, evidence, recovery and security. Open-source projects are replaceable components, never the Brain authority.

## Regional strategy

China and India are first-class source regions, alongside global open-source projects. Selection is capability- and license-based, not geographic preference.

## Current priority

The first target is the execution/autonomy gap: Brain-owned execution must remain authoritative and GitHub-hosted runners must never become an implicit fallback.

Next targets: research, multi-agent coordination, model routing, multilingual support, sandboxing, observability and media automation.

## Verification

This file records candidates and policy. It does not claim that any candidate has been integrated into Electronic Brain or passed its runtime gates.
