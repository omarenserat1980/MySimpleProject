# Brain Cloud VPS Kit

Turns an existing Ubuntu VPS into a Docker host for Brain Cloud.

## Fresh VPS

```bash
sudo bash bootstrap-ubuntu.sh
sudo BRAIN_APP_DIR=/opt/brain-cloud bash install-brain.sh
```

Set a strong BRAIN_CONTROL_TOKEN in /opt/brain-cloud/cloud/.env before exposing the API.

The kit installs Docker, Compose, Git and UFW, then runs the production Brain image with persistent volumes.

Only SSH/HTTP/HTTPS are opened by UFW. Keep port 8000 private behind TLS/reverse proxy.

These scripts configure an existing VPS; they do not create a paid cloud account or allocate a VM by themselves.