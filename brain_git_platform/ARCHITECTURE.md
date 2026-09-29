# Brain Git Platform Architecture

## Target topology

Brain Cloud
  -> Brain Git API
  -> Git storage
  -> Brain Runner Scheduler
  -> Brain Runners
  -> Artifact/Object storage
  -> Audit log

Optional:
  Brain Git Bridge <-> GitHub.com

## Core domains

### Repository
A repository has an immutable ID, namespace, name, default branch, storage path and visibility.

### Git
The Git service owns refs, commits, trees, blobs and repository locking. The application must never rewrite Git history implicitly.

### Review
Pull requests are Brain-native records referencing source and target refs. Reviews and merge decisions are stored independently of GitHub.

### Automation
A workflow is a Brain-native YAML/JSON definition. The scheduler creates a run, assigns a Brain runner, stores logs, and publishes artifacts.

### Security
All API calls are authenticated and authorized against Brain identities. Repository access is scoped. Runner credentials are short-lived.

## Isolation acceptance criteria

1. Brain startup succeeds with GitHub credentials absent.
2. Brain CI can clone/fetch/push from the Brain Git service.
3. Brain verification can create a branch and commit.
4. Brain workflows execute on Brain runners.
5. Artifacts and logs are retrievable without GitHub.
6. Disabling the optional bridge does not stop Brain runtime services.
7. GitHub URLs are not required in production configuration.
