# BRAIN Media Engine

Native project-owned media layer. The application owns the film model, scene graph,
timeline, procedural art, audio synthesis, preview renderer and QC manifests.

The browser is the runtime host, not an external media-making service.
Where available, WebCodecs provides native frame/audio encoding and decoding, while
Web Audio provides synthesis and mixing primitives. These are platform APIs, not
third-party production services.

## Modules
- scene graph
- timeline
- procedural renderer
- audio graph
- subtitle/caption renderer
- project manifest
- deterministic export
- QC/evidence
- commercial release gate


## Release evidence modules
- `qc_engine.py`: technical master validation
- `release_gate.py`: commercial gate
- `export_manifest.py`: master hash and evidence manifest

A release is blocked unless technical QC, rights evidence, story review, sound review and continuity review all pass.
