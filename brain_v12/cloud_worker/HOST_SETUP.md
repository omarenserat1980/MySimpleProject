# Brain Cloud Host

This runtime is a long-running .NET Worker Service designed for a user-owned Linux VM or server with Docker.

## Host requirements

- Linux x86_64 or arm64
- Docker Engine and Docker Compose
- Git
- outbound HTTPS access to GitHub and required Brain services
- persistent disk

## Install

1. Clone this repository into /opt/MySimpleProject.
2. Verify the production branch/commit.
3. Run: docker compose -f brain_v12/cloud_worker/compose.yml up -d --build
4. Install the service:
   sudo cp brain_v12/cloud_worker/brain-cloud-worker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now brain-cloud-worker
5. Verify with:
   sudo systemctl status brain-cloud-worker
   docker compose -f brain_v12/cloud_worker/compose.yml ps

## Live-host proof

The host is LIVE only after the process is observed running and worker heartbeat evidence is collected for multiple intervals. A successful GitHub build alone is not proof of a live host.

## Security

Do not put GitHub, Binance, payment, or private keys in this repository. Inject secrets through the host secret store/environment. Money movement and external publishing remain authorization-gated.

## Recovery

Docker uses restart: unless-stopped and systemd starts the service at boot. If the worker exits, Docker restarts it.
