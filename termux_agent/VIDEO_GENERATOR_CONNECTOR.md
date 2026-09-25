# Electronic Brain — GitHub-Centric Video Generator Connector

Repository: `omarenserat1980/MySimpleProject`
Branch: `main`

## Contract

The factory uses GitHub-managed code and manifest state, while the actual video
generation provider is injected at runtime.

Required runtime variable:

`VIDEO_GENERATOR_COMMAND`

The command receives:

- `SCENE_JSON`
- `OUTPUT_VIDEO`
- `FILM_ID`
- `PART_NUMBER`
- `TOTAL_PARTS`

It must create the requested MP4. The factory then uses FFmpeg to normalize
and verify the result as a 30-second 1920x1080 30fps H.264/AAC asset.

## Important

FFmpeg is not a video generator.

If `VIDEO_GENERATOR_COMMAND` is absent, the canonical state is:

`VIDEO_GENERATOR_NOT_CONNECTED`

Secrets and provider credentials must remain in runtime environment/secrets,
not in GitHub source files.

## Flow

GitHub manifest -> scene context -> video generator adapter -> generated MP4
-> FFmpeg normalize -> verification -> publisher.
