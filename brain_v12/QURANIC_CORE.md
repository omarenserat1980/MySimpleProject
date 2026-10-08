# Quranic Core — Electronic Brain

## Mission
Quranic Core is a source-grounded research and human-benefit layer. It helps Brain study Quranic material while keeping revelation, tafsir, human knowledge, scientific evidence, and Brain inference separate.

## Evidence hierarchy
- L0: Quran text
- L1: Hadith evidence
- L2: Tafsir
- L3: Language/context
- L4: Human knowledge
- L5: Scientific evidence
- L6: Research inference
- L7: Brain inference
- L8: Hypothesis

## Research gate
SOURCE_LOCK -> LANGUAGE_AND_CONTEXT -> TAFSIR_COMPARISON -> HUMAN_KNOWLEDGE -> SCIENTIFIC_CHECK -> COUNTER_EVIDENCE -> INTEGRITY_GATE -> HUMAN_BENEFIT -> PUBLISH_OR_HOLD

## Hard rules
1. Canonical Quran text is immutable inside Brain.
2. Brain inference can never be relabeled as Quranic text.
3. A Quran-text evidence record requires a citation.
4. Scientific claims remain scientific claims; they are not automatically Quranic interpretation.
5. Counter-evidence is a required stage before publication.
6. Insufficient evidence produces HOLD rather than fabrication.

## Source architecture
The canonical-text adapter should use a verified source such as Tanzil. Tanzil documents a highly verified Unicode text and states that changing the supplied text is not permitted. The Quranic Arabic Corpus documents that its annotated text is based on verified Tanzil text.

Live content such as tafsir and search can be connected through Quran Foundation server-side APIs. Credentials must remain server-side and must never be hard-coded.

## API
- GET /api/quranic-core/health
- GET /api/quranic-core/research-contract?question=...
- POST /api/quranic-core/research

## Next expansion
Add pinned canonical-text manifests, tafsir adapters, provenance records, counter-evidence workers, and human-benefit project generation. These adapters must remain behind the integrity gate.
