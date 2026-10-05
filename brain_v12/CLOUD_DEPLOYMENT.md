# Brain Cloud Deployment Contract

Brain production execution is hosted in the Brain Cloud stack.

## Components

- `brain-api`: FastAPI control/API surface.
- `brain-cloud-runtime`: durable Brain-owned execution worker.
- Docker volumes: persistent queue, checkpoints, evidence, and Brain data.
- GitHub: source, review, release metadata, and evidence only.

## Deploy

On a user-owned Linux x86_64 Cloud VM with Docker:

```bash
./tools/brain_cloud_preflight.sh
docker compose -f docker-compose.brain-cloud.yml up -d --build
curl -fsS http://127.0.0.1:8012/health
```

The public service must be placed behind HTTPS/reverse proxy. Do not expose
the raw application port directly to the public internet without an
appropriate firewall and authentication policy.

## Independence invariant

The cloud runtime does not register as a GitHub Actions runner. It executes
from its own durable queue and worker process.

A GitHub outage must not stop already-running production tasks. GitHub may be
used later for source synchronization, release publication, and evidence
upload when available.

## Verification

Deployment is not considered verified until all are true:

1. API health returns 200.
2. `/health` reports `state=RUNNING` from a fresh `brain-cloud-runtime` heartbeat; environment flags alone are not accepted as proof.
3. Cloud runtime worker is running.
4. Internal runner preflight passes.
5. A durable task survives worker restart.
6. A task executes and produces evidence.
7. Recovery replays pending work correctly.
8. GitHub-hosted execution is not involved.
9. The authority gate blocks an unverified runner.

Only then can the autonomy certification be evaluated.
