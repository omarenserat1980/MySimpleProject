# Wan2.1 on RunPod

This worker runs the open-source Wan2.1 T2V-1.3B model on a RunPod Serverless GPU endpoint.

## Required endpoint environment

- `WAN_MODEL_DIR`: path containing the downloaded Wan2.1 T2V-1.3B checkpoint.
- `WAN_OUTPUT_DIR`: optional output directory.

The checkpoint should be placed on a RunPod Network Volume so workers do not redownload it on every cold start.

The Electronic Brain client uses:

- `RUNPOD_API_KEY`
- `RUNPOD_ENDPOINT_ID`
- optional `RUNPOD_BASE_URL` (defaults to `https://api.runpod.ai/v2`)

Job input:

```json
{"input":{"prompt":"...","size":"832*480"}}
```

For a production YouTube pipeline, the returned MP4 should be uploaded by the worker to S3-compatible storage and returned as a URL; this is intentionally kept separate from the GPU worker credentials.
