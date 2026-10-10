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

## Manual, gated GitHub Actions deployment

The `Brain Cloud Deploy` workflow runs **only when manually dispatched** with the exact `confirm_deploy` input `DEPLOY`. It does not provision a host or deploy on every push. Configure the `production` GitHub Environment (with approvals if desired), and provide these secrets at the repository or environment level:

- `BRAIN_CLOUD_SSH_HOST`: hostname or IP of an **existing** host
- `BRAIN_CLOUD_SSH_USER`: SSH user allowed to run Docker Compose
- `BRAIN_CLOUD_SSH_KEY`: private SSH key (keep secret; do not commit)
- `BRAIN_CLOUD_SSH_KNOWN_HOSTS`: trusted SSH host-key entry, verified independently before storing (do not blindly trust `ssh-keyscan` output)

Set GitHub Actions variable `BRAIN_CLOUD_REMOTE_DIR` to the absolute directory on that host containing `docker-compose.production.yml` and `.env` (for example `/opt/brain-cloud`). For safe remote-shell handling, use only letters, digits, dots, underscores, slashes, and hyphens; do not include spaces or shell metacharacters. That directory must be provisioned in advance; the workflow does not copy files or install Docker. Install Python 3 and curl on the host for readiness checks. Set `BRAIN_PORT=8000` or leave it unset for the workflow's current localhost smoke check. Ensure `BRAIN_CONTROL_TOKEN` in `.env` is at least 32 characters, and restrict `.env` permissions. If the GHCR package is private, authenticate Docker on the host with read-only package access before running the workflow. Do not expose package credentials in logs.

After confirming the host and credentials are ready, open **Actions → Brain Cloud Deploy → Run workflow**, enter `DEPLOY`, and review the run result. A successful run proves container health on that host, not public HTTPS reachability or long-term uptime. Public TLS and persistence must be verified separately.

Do not expose port 8000 directly to the public Internet; place TLS, access control and rate limiting in front of the API.
