# ELECTRONIC BRAIN — GITHUB FIRST POLICY

## Purpose
GitHub is the control plane and first coordination point for Electronic Brain programming, execution, factory, deployment, and automation requests.

## Mandatory sequence
For every Electronic Brain request:
1. Connect to `omarenserat1980/MySimpleProject`.
2. Verify branch `main`.
3. Read the relevant source, manifest, state, and contracts before acting.
4. Reuse VERIFIED/PUBLISHED work; never regenerate it without an explicit recovery reason.
5. Execute the smallest safe next operation.
6. Verify the result with an independent check.
7. Persist state/audit information.
8. Commit material code/configuration changes to GitHub.
9. Continue automatically to the next eligible operation.

## Video factory
The canonical pipeline is:

`GITHUB → LOAD STATE → GENERATE → NORMALIZE → VERIFY → PUBLISH → SAVE STATE → GITHUB → NEXT`

The 30-minute cinematic target is 60 independent 30-second videos. Completion is allowed only at 60/60 VERIFIED and 60/60 PUBLISHED.

## Provider boundaries
GitHub orchestrates the factory but is not itself a video-generation provider. A real provider must be connected through `VIDEO_GENERATOR_COMMAND` (or an equivalent authenticated runtime bridge). FFmpeg is normalization/verification only.

Publishing requires a real authenticated publisher. The factory must never report PUBLISHED without verified publisher output/evidence.

## Secrets
Provider credentials, OAuth tokens, API keys, and private media URLs must remain in runtime secrets/environment variables and never be committed to GitHub.

## No false completion
Never report generation, verification, deployment, or publication as complete unless the runtime produced independently verifiable evidence.

## Failure handling
On failure:
- persist the exact error and operation state;
- retry when the failure is transient and safe;
- do not repeat VERIFIED/PUBLISHED work;
- stop only at a hard dependency boundary that cannot be satisfied by available connected tools.

## Human authorization
External side effects that require an unavailable account connection, OAuth consent, purchase, or provider connection remain blocked until that dependency is explicitly connected. The system must continue all independent work without waiting on unrelated tasks.
