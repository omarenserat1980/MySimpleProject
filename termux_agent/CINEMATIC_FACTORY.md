# PHONE-ONLY Cinematic Factory

The Brain now contains a resumable 60-part cinematic executor.

## Contract
- 60 MP4 files
- exactly 30 seconds each
- total story runtime: 1800 seconds
- sequential story continuity
- verify before publish
- persist state after every part
- never regenerate a verified part

## Termux
Run from the repository root:

```bash
export CINEMATIC_FACTORY_ROOT="$PWD"
export VIDEO_RENDER_COMMAND='YOUR_VIDEO_RENDERER_COMMAND'
export PUBLISH_COMMAND='YOUR_PHONE_PUBLISHER_COMMAND'
python termux_agent/cinematic_factory.py
```

For each part the renderer receives:
- `SCENE_JSON`: complete scene JSON
- `OUTPUT_VIDEO`: required output path

The publisher receives:
- `VIDEO_FILE`
- `PART_NUMBER`
- `VIDEO_TITLE`
- `VIDEO_DESCRIPTION`

The publisher must return exit code 0 only after the external platform confirms the upload.

## Important
FFmpeg performs normalization and technical verification; it does not generate cinematic footage. A real video-generation provider must be connected through `VIDEO_RENDER_COMMAND`.

YouTube OAuth/API credentials must remain in environment variables or a secure secret store, never in Git.
