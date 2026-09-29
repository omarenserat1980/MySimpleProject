# Brain Cloud Production Runtime

GitHub publishes the Brain Cloud image to GHCR. A Docker-compatible cloud host runs that immutable application image with persistent volumes.

## Host requirements

- Linux VM/VPS or Docker-compatible cloud host
- Docker Engine and Compose
- HTTPS egress to GHCR
- Reverse proxy/TLS for public access

## Deploy

Copy this directory's compose file to the host and create `.env` from `cloud/.env.production.example`. Set a strong `BRAIN_CONTROL_TOKEN` and only the provider credentials you need.

Then:

```bash
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
```

The named volumes preserve Brain state and cinematic output across image updates.

## Automatic deployment

The `Brain Cloud Deploy` GitHub Actions workflow can deploy automatically over SSH. Configure these repository secrets:

- `BRAIN_CLOUD_SSH_HOST`
- `BRAIN_CLOUD_SSH_USER`
- `BRAIN_CLOUD_SSH_KEY`

The target host must already have Docker Compose and the production `.env`.

Do not expose port 8000 directly to the public Internet; place TLS, access control and rate limiting in front of the API.
