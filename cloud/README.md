# Brain 6 Cloud Runtime

This directory is the provider-neutral cloud runtime for Electronic Brain.

It does not require Render and does not require a self-hosted GitHub Runner. The container can run on any cloud VM/container platform that supports Docker.

## Runtime

`brain_cloud.py` supervises the existing Brain 7 cinematic factory, restarts the production cycle after each completed slice, keeps state/output on persistent volumes, and stops cleanly on SIGTERM/SIGINT.

## Required media provider

A real media provider must be configured through secrets/environment variables. The runtime deliberately does not create fake video when real media is required.

## Start

1. Copy `.env.example` to `.env` and add secrets in the cloud secret manager.
2. Start with `docker compose -f cloud/docker-compose.yml up -d --build` from the repository root.
3. Inspect with `docker compose -f cloud/docker-compose.yml logs -f brain`.

The GitHub repository remains source control/CI. The cloud container is the long-running Brain process.
