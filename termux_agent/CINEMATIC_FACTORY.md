# BRAIN Media Engine — Cinematic Factory

BRAIN Media Engine is the unified media control plane for the cinematic pipeline. The existing resumable 60-part executor remains the runtime worker, while media operations, normalization and QC are owned by the Media Engine contract.

## Contract
- 60 MP4 files
- exactly 30 seconds each
- total story runtime: 1800 seconds
- sequential story continuity
- verify before publish
- persist state after every part
- never regenerate a verified part

## BRAIN Termux Emulator
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
BRAIN Media Engine performs normalization, composition and technical verification. FFmpeg remains an internal execution dependency only; there is no separate FFmpeg GUI or user-facing FFmpeg workflow. A real video-generation provider may be connected through `VIDEO_RENDER_COMMAND`, while the resulting media is handed back to BRAIN Media Engine for processing and QC.

YouTube OAuth/API credentials must remain in environment variables or a secure secret store, never in Git.
