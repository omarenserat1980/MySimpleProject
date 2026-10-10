# Brain GPT — 20-Layer Architecture

## Objective
Build a first-party, ChatGPT-like experience inside Electronic Brain with twenty explicit orchestration layers. The layer registry is an architecture contract, not a claim that all integrations are already operational.

## The 20 layers
1. **Input Gateway** — normalize user input and request metadata.
2. **Identity & Access** — validate identity, scope, and access policy.
3. **Conversation Manager** — resolve session and conversation state.
4. **Context Builder** — assemble bounded, relevant conversation context.
5. **Memory Retrieval** — retrieve permitted persistent memories.
6. **Knowledge Retrieval** — retrieve available files and trusted knowledge.
7. **Intent Router** — classify intent and task category.
8. **Task Planner** — define a bounded plan and success criteria.
9. **Model Router** — select an available model and fallback.
10. **Reasoning Adapter** — invoke the selected model for analysis or generation.
11. **Response Guard** — check output shape, uncertainty, and policy constraints.
12. **Tool Planner** — choose registered tools and validate arguments.
13. **Permission Gate** — require approval for protected actions.
14. **Execution Dispatcher** — dispatch approved work to existing Brain executors.
15. **Result Collector** — collect tool outputs and execution metadata.
16. **Verification Gate** — verify outcomes against explicit criteria.
17. **Recovery Controller** — bound retries and propose safe recovery actions.
18. **Audit & Evidence** — record provenance, decisions, and evidence references.
19. **Memory Consolidation** — persist eligible session outcomes and summaries.
20. **Response Delivery** — return answer, status, and evidence disclosure.

## Existing capabilities to reuse
- `brain_v12/brain/brain_ai.py` for the existing AI facade and governed tool loop.
- `brain_v12/brain/model_router.py` for model selection and fallback.
- `brain_v12/brain/chat_session_store.py` and `chat_session_api.py` for persistent sessions and per-session memory.
- Existing supervisor, permission, evidence, and verification components where compatible.

## Runtime diagnostics API

The current integration exposes a read-only endpoint:

`GET /api/brain-ai/layers/status`

It returns the twenty ordered layers with `READY`, `PARTIAL`, or `NOT_WIRED` statuses, aggregate counts, and `execution_performed: false`. This endpoint is diagnostic only; it does not invoke a model or execute tools. It must report `INTEGRATION_INCOMPLETE` while any layer is not fully ready.

The application injects its persistent `ChatSessionStore` into this diagnostics route so session, context, and memory adapters can be detected. Model readiness is counted only when the router confirms a selectable chat model.

## Contract implementation
`brain_v12/brain/brain_gpt_20_layer_pipeline.py` defines the ordered layer contract and requires an explicit handler for every required layer. It fails closed when configuration is incomplete, a layer fails, or a handler raises an exception. This avoids treating an architecture diagram as a working deployed system.

## API integration plan
1. Wire status into Brain AI diagnostics only after reviewing current application initialization.
2. Add a dedicated endpoint only after authentication and dependency injection are confirmed.
3. Register adapters around existing modules; do not duplicate memory, model, or executor systems.
4. Add end-to-end tests for context isolation, approvals, provider failure, restart persistence, and evidence integrity.
5. Keep high-risk tools behind explicit approval. Never expose provider credentials in browser code.
6. Do not merge or declare production-ready until CI and a runtime smoke test pass.

## Definition of done
- Exactly twenty unique, ordered layers.
- All required adapters explicitly registered.
- Incomplete configuration blocks execution with a machine-readable reason.
- Failure stops downstream execution and returns evidence.
- Unit and end-to-end tests pass in CI.
- Existing APIs remain backward compatible.
- Runtime status distinguishes configured, ready, and unverified states.
