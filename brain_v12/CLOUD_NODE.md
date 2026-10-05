# Brain Cloud Node

A Brain Cloud Node is a user-owned Linux x86_64 machine running the Brain API and
Brain Cloud Runtime directly through Docker. It is an execution environment,
not a GitHub Actions runner.

## Invariant

GitHub is used for source control, review, release, and evidence. It is not the
runtime scheduler or execution engine.

## Start

From the repository root:

    ./tools/run_brain_cloud_node.sh

The launcher requires Docker and Docker Compose and performs the existing Brain
Cloud preflight. It only reports VERIFIED when the API observes a fresh
preflight-verified cloud worker heartbeat.

## Minimum host

- Linux x86_64
- Docker Engine + Compose
- persistent disk
- network access
- QEMU tooling available inside the Brain image

For Windows/QEMU workloads, use substantially more CPU/RAM/storage than the
minimum needed for API/worker proof.

## Migration

The same compose stack can move from a temporary user-owned host to a future
cloud VM. No GitHub Actions runner registration is required.
