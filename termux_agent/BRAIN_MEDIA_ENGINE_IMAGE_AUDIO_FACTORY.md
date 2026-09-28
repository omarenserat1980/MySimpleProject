# BRAIN Media Engine — Image + Audio Factory

This factory is a production profile of **BRAIN Media Engine** for building cinematic scenes from still images plus audio.

## Pipeline

1. Select and order the scene images.
2. Prepare narration, music and other audio assets.
3. BRAIN Media Engine renders motion from stills and synchronizes audio.
4. Normalize to 1920×1080, 30 fps, H.264/AAC by default.
5. Run Media Engine QC for duration, video/audio streams, dimensions and file integrity.
6. Publish only after the quality gate passes.
7. Persist state and continue to the next part.

## Architecture

- **User-facing interface:** BRAIN Media Engine.
- **Control plane:** Electronic Brain.
- **Execution runtime:** the configured local media runtime.
- **FFmpeg/FFprobe:** internal implementation dependencies only; they are not a separate GUI or user-facing product.

Target: 60 independent videos × 30 seconds, sequentially forming one film.
