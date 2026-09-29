# Brain Cloud Runtime

This directory contains the provider-neutral long-running runtime for Electronic Brain.

## Runtime

- GitHub is the source-control and CI layer.
- Brain Cloud runs the long-lived API and workers.
- Secrets belong in the Brain Cloud environment/secret manager.
- The runtime can build and run locally with Docker Compose for verification.

## Start

1. Copy `.env.example` to the Brain Cloud secret/environment configuration.
2. Build and start with `docker compose -f cloud/docker-compose.yml up -d --build`.
3. Inspect with `docker compose -f cloud/docker-compose.yml logs -f brain`.

The Brain API is served by `brain_v12.app:app`; the authenticated Cloud Hub is served by `cloud.api_server:app`.
