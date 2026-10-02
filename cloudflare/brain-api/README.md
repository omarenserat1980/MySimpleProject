# Brain Cloud HTTPS Adapter

This adapter provides a public HTTPS edge in front of the existing Brain Cloud .NET Worker.

Architecture:

Browser / PWA
  -> Cloudflare Worker (HTTPS edge)
  -> BRAIN_ORIGIN
  -> BrainCloudWorker (.NET)
  -> Brain Supervisor / workers

The adapter is intentionally thin. It does not run FFmpeg, .NET, or long-running jobs.

## Required deployment configuration

Set the Cloudflare Worker variable:

- BRAIN_ORIGIN = the real HTTPS origin of the user-owned Brain Cloud Worker.

Do not put API keys in this repository. If upstream authentication is required, configure it as a Cloudflare secret and extend the adapter to inject it.

## Verification

1. Deploy the Worker.
2. Open GET /health.
3. Verify the response is JSON with ok=true and service=brain-cloud-api.
4. Verify GET /api/brain/status reaches the .NET Worker.
5. Only then configure the browser application with the public HTTPS URL.

Cloudflare Workers Free currently provides 100,000 requests/day and 10 ms CPU time per invocation, so this component should remain a lightweight proxy/control-plane layer rather than the FFmpeg runtime.
