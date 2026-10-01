# GitHub Brain — Architecture and Migration Contract

## Mission
GitHub Brain is the Brain-owned source-control and automation control plane. External GitHub is an optional mirror/bridge, never a runtime dependency.

## Authority
BRAIN_GIT_PRIMARY is authoritative for internal repositories, branches, commits, issues, pull requests, artifacts, CI jobs, audit records, and recovery metadata.

## Compatibility
The repository engine must remain Git-compatible so standard Git clients can clone, fetch, pull, branch, commit, merge, and push.

## Separation
The Brain application depends only on the Brain Git API/adapter. The external GitHub adapter is optional and must be disabled by default.

## Execution
Brain Workflow owns:
Discover → Plan → Select Backend → Execute → Verify → Repair → Retry → Deliver.

GitHub Brain CI owns jobs and artifacts; Brain Supervisor owns policy and verification.

## Migration
1. Inventory and dependency scan.
2. Establish Brain Git service.
3. Build adapter/API contract.
4. Import repositories and verify object integrity.
5. Move Brain CI execution away from GitHub Actions.
6. Run dual-read/dual-verification.
7. Prove operation with GitHub unavailable.
8. Cut over authority.
9. Keep GitHub as optional export/mirror.
10. Remove mandatory GitHub credentials/dependencies.

## Gate
No phase is accepted without reproducible test evidence. No "100%" claim is allowed until the Independence Gate passes.
