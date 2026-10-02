# Global AI Radar

This registry contains only AI backends recommended for Electronic Brain evaluation.

Selection rules:
- free/open-source first
- self-hostable where practical
- replaceable adapters, never hard dependencies
- independent verification required
- no agent may declare its own success
- paid APIs may be used only as optional adapters

Recommended initial set:
- OpenCode — primary coding-agent backend
- OpenHands — autonomous software-development backend
- Goose — MCP/tool-orchestration backend
- Qwen Code — Qwen/Asia-oriented coding backend
- Ollama — local model runtime
- vLLM — cloud/GPU model serving runtime
- OpenShell — security sandbox candidate; evaluation required before production

Sources are recorded in global_ai_radar.json and must be revalidated before production promotion.
