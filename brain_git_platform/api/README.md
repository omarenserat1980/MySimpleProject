# Brain Git API

Initial API contract for the internal platform.

## Planned endpoints

- GET /api/v1/repos
- POST /api/v1/repos
- GET /api/v1/repos/{namespace}/{name}
- POST /api/v1/repos/{namespace}/{name}/branches
- GET /api/v1/repos/{namespace}/{name}/commits
- POST /api/v1/repos/{namespace}/{name}/commits
- POST /api/v1/repos/{namespace}/{name}/pulls
- POST /api/v1/repos/{namespace}/{name}/pulls/{id}/merge
- POST /api/v1/repos/{namespace}/{name}/workflows/{workflow}/dispatch
- GET /api/v1/runs/{id}
- GET /api/v1/runs/{id}/logs
- GET /api/v1/runs/{id}/artifacts

The contract deliberately avoids GitHub-specific response shapes so Brain remains portable.
