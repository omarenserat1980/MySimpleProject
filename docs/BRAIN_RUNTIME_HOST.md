# Brain Runtime Host

This is the provider-neutral persistent runtime for Brain Web App v2.

## Flow

Browser/PWA -> HTTPS reverse proxy or tunnel -> Brain Cloud Worker -> Brain Web/API.

The runtime does not require Render or a paid media API.

## Start

From the repository root on a machine that stays online:

```bash
export BRAIN_CLOUD_API_KEY='replace-with-a-long-random-secret'
docker compose -f brain_v12/cloud_worker/docker-compose.runtime.yml up -d --build
```

Verify locally:

```bash
curl http://127.0.0.1:8080/health
```

The response must contain `"ok":true` and `"state":"RUNNING"`.

## HTTPS

Do not expose port 8080 directly to the public internet. Put an HTTPS reverse proxy or an authorized HTTPS tunnel in front of it.

The resulting HTTPS origin can then be supplied to Brain Web App v2 runtime configuration.

## Security

- Keep `BRAIN_CLOUD_API_KEY` secret.
- Bind the runtime locally by default.
- Use TLS at the edge.
- Do not mark the web app connected until `/health` succeeds through the configured HTTPS origin.
- GitHub Actions remains CI/automation, not the persistent runtime host.

## No fake deployment

These files provide the runtime package only. They do not claim that a public runtime exists. A real always-on host and an authorized HTTPS endpoint are still required before adding an origin to `config.json`.
