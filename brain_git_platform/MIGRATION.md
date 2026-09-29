# Migration Plan: GitHub -> Brain Git Platform

## Phase 1 — Internal boundary
Create the repository/service contracts and make Brain code target the internal API.

## Phase 2 — Native Git storage
Provision bare Git repositories in Brain storage and expose authenticated smart HTTP/SSH access.

## Phase 3 — Native automation
Move verification, cinematic factory, Android builds and repair workflows to Brain runners.

## Phase 4 — Native artifacts and audit
Move workflow logs, artifacts, run metadata and audit events to Brain storage.

## Phase 5 — Bridge-only GitHub
Keep GitHub as an explicit import/export/mirror integration.

## Phase 6 — Detach
Remove GitHub credentials and direct GitHub API calls from Brain production environments. Run the isolation acceptance suite before disabling the bridge.

Rollback remains possible until Phase 6 by restoring the bridge configuration.
