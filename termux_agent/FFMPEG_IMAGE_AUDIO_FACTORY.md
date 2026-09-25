# FFmpeg Image + Audio Factory

The cinematic factory may produce each 30-second part entirely from still images plus audio; no AI video generator is required.

Pipeline:
1. Select/prepare ordered still images for the scene.
2. Prepare narration/music/audio.
3. FFmpeg creates motion from stills (zoom/pan/crossfade) and synchronizes audio.
4. Normalize to 1920x1080, 30fps, H.264/AAC.
5. Verify duration, video stream, audio stream and dimensions.
6. Publish only after verification.
7. Persist state and continue to the next part.

FFmpeg is the production engine in this mode, not merely a verifier.

Runtime inputs can be supplied through the existing factory command using image/audio assets; secrets remain outside Git.

Target remains 60 independent videos × 30 seconds, sequentially forming one film.
