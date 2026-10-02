# Global AI Radar

This registry contains only AI backends recommended for Electronic Brain evaluation.

Selection rules:
- free/open-source first
- self-hostable where practical
- replaceable adapters, never hard dependencies
- independent verification required
- no agent may declare its own success
- paid APIs may be used only as optional adapters

The radar now covers global coding agents, model runtimes, security runtimes, Indian-language AI, Japanese research, Taiwanese language models, Korean models, Chinese OCR/compute paths, European models, and Arabic-first models.

## Evidence-first evaluation

`global_ai_radar_evaluator.py` converts each registry candidate into a bounded evaluation plan:

Discover → License Check → Capability Test → Security Test → Benchmark → Evidence Review → Adapter Validation → Verify

Every stage starts as `PENDING`. Promotion is forbidden until independent evidence exists for all required stages. A successful process exit is not treated as proof of capability or correctness.

Sources are recorded in `global_ai_radar.json` and must be revalidated before production promotion.
