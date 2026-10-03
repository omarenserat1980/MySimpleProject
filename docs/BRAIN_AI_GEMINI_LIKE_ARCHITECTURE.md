# Brain AI — Gemini-like Architecture

## Goal

Build a first-party AI experience inside Electronic Brain with a unified conversational surface while keeping models, memory, tools, permissions, and verification as separate layers.

## Current implementation

- \`brain_v12/brain/brain_ai.py\` — Brain AI facade.
- \`brain_v12/brain/brain_ai_api.py\` — HTTP API under \`/api/brain-ai\`.
- Existing \`OpenAIProvider\` remains the model adapter; Brain AI is not coupled to a single model.
- Existing \`MemoryStore\` and \`CognitiveLoop\` provide context.
- Tool execution is explicit and permission-aware.
- High-risk tools require explicit approval.
- Tool results are returned as evidence; no implicit success.

## API

### GET /api/brain-ai/status

Returns provider, memory, cognitive-loop and registered-tool status.

### POST /api/brain-ai/chat

Request:

\`\`\`json
{"message":"حلل حالة المشروع","instructions":""}
\`\`\`

### POST /api/brain-ai/tool

Request:

\`\`\`json
{"name":"tool.name","params":{},"approved":false}
\`\`\`

## Evolution path

1. Connect the existing web chat to Brain AI without breaking the legacy endpoint.
2. Add constrained structured tool selection.
3. Add multimodal context adapters for images, files and audio.
4. Add streaming responses.
5. Add model routing and fallbacks.
6. Add persistent conversation/session state.
7. Add Brain-specific verification and audit events for every tool call.
8. Add a dedicated Brain AI web surface with a modern multimodal assistant experience while retaining Brain identity and controls.

## Safety principles

- Never place API keys in browser code.
- Never claim a tool action succeeded without evidence.
- Keep high-risk actions behind explicit approval.
- Keep the model provider replaceable.
