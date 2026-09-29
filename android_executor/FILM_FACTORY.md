# Electronic Brain — Cinematic Film Factory

## Pipeline
PROJECT -> STORY -> SCENES -> ASSETS -> QUEUE -> FFmpeg RENDER -> VERIFY -> FINAL MASTER

The phone is the execution node. The Brain/orchestrator supplies creative plans and task definitions.

## Modern Android stack
- Android native/Kotlin
- Media3 1.11.1 for playback/preview
- FFmpeg 9.0.2 target for packaged/native media processing
- Persistent Queue/Resume
- SHA-256 artifact verification
- App-private execution state + factory output directory

FFmpeg 9.0.2 is the current stable 9.0 branch release as of 18 Sep 2026. Media3 1.11.1 is the current stable release as of 10 Sep 2026.

## Production stages
1. Create film project.
2. Decompose into scenes.
3. Prepare scene folders.
4. Import/generate image, video and audio assets.
5. Render scene with FFmpeg.
6. Verify every artifact.
7. Assemble final master.
8. Resume unfinished work after interruption.
