# Brain Film Hub

A dedicated Brain-owned video interface, conceptually similar to a video platform but separate from YouTube.

Architecture:

C++ verified renderer -> MP4 + manifest -> C# Film Hub -> dedicated web clients

The hub stores film metadata and verified artifact references. It must never mark a film published merely because a render command returned zero; the manifest must contain VERIFIED_COMPLETED and master QC evidence.

Future endpoints:
- GET /api/films
- GET /api/films/{id}
- GET /api/films/{id}/stream
- POST /api/films
- POST /api/films/{id}/publish

Publishing is permission-controlled. YouTube integration remains a separate adapter.
