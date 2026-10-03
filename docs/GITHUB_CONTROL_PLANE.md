# Brain GitHub Control Plane

Electronic Brain must not treat GitHub as only a Workflow runner.

The Control Plane is the Brain-owned policy boundary for repositories, Git data, files, branches, commits, Issues, Pull Requests/reviews, Actions, Releases, Packages, Projects, Security, Search, users/organizations and webhooks.

## Execution contract

`discover -> authorize -> execute -> verify -> audit`

Read operations may run when credentials are configured. Mutating operations require explicit approval. A successful HTTP response is transport evidence only; Brain verification remains mandatory.

## Current relationship

- `BrainGitService`: Brain-owned Git repository primitives.
- `Code Hub`: human-facing repository/file UI.
- `dispatch_workflow.py`: Actions-specific execution.
- `GitHubControlPlane`: unified GitHub API policy/execution boundary.
