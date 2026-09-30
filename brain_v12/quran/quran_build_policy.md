# BRAIN Quran Build Policy

## Objective

Process the complete Quran from the first ayah to the last ayah while preserving
a strict boundary between the Quran text, attributed interpretation, analysis,
and engineering hypotheses.

## Per-ayah pipeline

1. Register the exact source text and verse key.
2. Verify source integrity with SHA-256.
3. Record surah and ayah identifiers.
4. Attach tafsir only when a named source and citation are present.
5. Record linguistic/topic observations separately from tafsir.
6. Record causal observations only with explicit evidence.
7. Record engineering ideas as hypotheses until independently verified.
8. Audit the record before it can influence Brain decisions.

## Non-negotiable rules

- Do not rewrite or alter the Quran text.
- Do not present an AI-generated interpretation as tafsir.
- Do not turn a verse into a scientific law without independent evidence.
- Keep source attribution for every tafsir/translation.
- Keep hypotheses, observations, and verified facts separate.
- A missing interpretation is a valid state; it is not a failure.

## Source policy

The primary digital Arabic text may use a precisely identified source such as
Tanzil, with attribution and license requirements preserved. Tanzil states that
its Quran text should be redistributed verbatim and not changed, and that
applications should identify Tanzil and link back to it.

The current build therefore stores hashes and identifiers rather than silently
transforming the source text.

## Completion condition

The Quran layer is complete only when all 6236 ayah records exist and pass
integrity checks. Semantic analysis is a separate, auditable phase and does
not block text registration.
