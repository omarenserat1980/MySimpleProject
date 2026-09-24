# Render deployment synchronization marker

This marker intentionally triggers a fresh Render deployment from `main` after the V12 deployment synchronization fix.

Expected runtime version: `12.6`.

Expected verification endpoints:
- `/health`
- `/api/deploy/identity`
- `/api/problem/solve`
