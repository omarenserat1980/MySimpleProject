# Brain Open-Source AI Fabric

## Purpose

Brain can use open-source projects from India and China as **replaceable capability providers**. They are not allowed to become hidden execution paths.

The integration boundary is:

ChatGPT / planner
→ Brain Control Plane
→ Capability Resolver
→ Open-Source Provider Registry
→ approved runtime adapter
→ Executor Router
→ evidence
→ Verification Gate

## Initial provider set

### India

- **AI4Bharat IndicTrans2** — translation for 22 scheduled Indian languages.
- **AI4Bharat IndicF5** — multilingual TTS for 11 Indian languages.

### China

- **Qwen3** — LLM/reasoning/tool-use.
- **DeepSeek-V3** — LLM/reasoning/coding.
- **OpenBMB MiniCPM** — local/on-device LLM and multimodal capabilities.

## Rules

1. Registry entries are metadata only.
2. No provider is downloaded or executed automatically.
3. Exact model/license terms must be checked before production redistribution.
4. Runtime execution must go through Brain's existing executor policy and single-flight controls.
5. Provider failure must produce evidence and may not spawn an uncontrolled parallel fallback.
6. A provider may be replaced without changing Brain's core orchestration contract.

## Recommended first deployments

- Arabic/Indic translation: IndicTrans2 adapter.
- Indian-language narration: IndicF5 adapter.
- Lightweight local agent on constrained hardware: MiniCPM.
- General local reasoning/coding: Qwen3 or DeepSeek, subject to hardware and exact model-license review.

## Upstream references

- https://github.com/AI4Bharat/IndicTrans2
- https://github.com/AI4Bharat/IndicF5
- https://github.com/QwenLM/Qwen3
- https://github.com/deepseek-ai/DeepSeek-V3
- https://github.com/OpenBMB/MiniCPM
