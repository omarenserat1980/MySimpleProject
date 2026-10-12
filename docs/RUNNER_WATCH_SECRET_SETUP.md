# Brain Runner Watch Secret Bootstrap

This helper safely validates and stores the repository Actions secret required by
`.github/workflows/brain-permanent-runner-watch.yml`.

## Run

From a trusted terminal with GitHub CLI installed and authenticated:

```bash
bash scripts/github/create_runner_watch_secret.sh
```

Optionally pass a repository:

```bash
bash scripts/github/create_runner_watch_secret.sh omarenserat1980/MySimpleProject
```

The script:
1. Disables shell tracing and reads the candidate token without echoing it.
2. Tests the candidate token against `GET /repos/OWNER/REPO/actions/runners?per_page=1`.
3. Refuses to change the secret if that API request fails.
4. Pipes the value to `gh secret set` over stdin; it never prints the token or places it in command-line arguments.

## Required permissions

Two separate credentials/permission checks apply:

- **Candidate value being stored as `BRAIN_RUNNER_WATCH_TOKEN`:** must be authorized to read the repository self-hosted runner administration endpoint. For a fine-grained token, try repository `Administration: Read-only` if supported by the account and endpoint.
- **The identity used by `gh auth login`:** must be allowed to write repository Actions secrets (commonly repository `Actions: write` with the required repository access). The script does not elevate permissions or create a PAT for you.

Do not paste tokens into chat, commit them, put them in shell history, or enable `set -x`. The script intentionally emits only sanitized status.

## After running

Open the [Brain Permanent Runner System Watch workflow](https://github.com/omarenserat1980/MySimpleProject/actions/workflows/brain-permanent-runner-watch.yml) and run it. Require all of the following:
- no `API_PERMISSION_DENIED` / HTTP 403;
- the runner matches the required labels and is `online`;
- the explicit execution probe passes.

A successful secret write alone does not prove runner connectivity or Windows Server 2025 boot.
