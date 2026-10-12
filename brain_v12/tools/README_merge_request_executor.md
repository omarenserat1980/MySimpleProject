# Brain Merge Request Executor

A guarded pull-request merge tool for the Electronic Brain repository. It is an execution adapter, not a parallel workflow: invoke it from the existing Brain Task / Primary Pipeline after review and verification.

## Safety contract

- Dry-run is the default. No merge happens without the explicit `--execute` flag.
- Requires an open, non-draft PR, confirmed mergeability, an approved review, and non-empty successful check evidence.
- Re-fetches the PR immediately before merge and blocks if the head SHA changed.
- Uses GitHub's normal merge endpoint through `gh`; branch protection and GitHub permissions remain authoritative.
- Never force-pushes, dismisses reviews, bypasses checks, or edits protection rules.
- Writes JSONL audit evidence. A successful CLI exit is not enough: it re-reads the PR and verifies the merged postcondition.

## Setup

Install GitHub CLI and authenticate it with the minimum repository permissions required to inspect and merge pull requests. Run from the repository checkout or supply `--repo owner/name`.

## Use

Inspect only:

```bash
python -m brain_v12.tools.merge_request_executor 325 --repo omarenserat1980/MySimpleProject
```

Execute only after reviewing the dry-run evidence:

```bash
python -m brain_v12.tools.merge_request_executor 325 --repo omarenserat1980/MySimpleProject --execute --expected-head EXPECTED_HEAD_SHA
```

The tool exits 0 for ready dry-run or verified merge, 2 when a gate blocks, 3 when the merge postcondition cannot be verified, and 4 for command/API errors. Audit output defaults to `brain6_artifacts/merge_requests/audit.jsonl`.

## Known boundary

This adapter currently targets GitHub pull requests through `gh`. Brain Git remains the internal repository authority. Do not treat a GitHub mirror merge as proof that Brain Git was updated; the existing synchronization/verification gate must confirm that separately.
