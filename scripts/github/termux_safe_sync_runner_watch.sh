#!/usr/bin/env bash
# Safe Termux recovery for a diverged Brain checkout, then run the runner-watch secret tool.
# Does not reset, force-push, bypass signed execution contracts, or print credentials.
set -Eeuo pipefail
set +x
umask 077

REPO_DIR="${BRAIN_REPO_DIR:-$HOME/MySimpleProject}"
REMOTE="${BRAIN_GIT_REMOTE:-origin}"
BRANCH="${BRAIN_GIT_BRANCH:-main}"
SECRET_TOOL="scripts/github/create_runner_watch_secret.sh"

die() { printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null 2>&1 || die "git is not installed."
[[ -d "$REPO_DIR/.git" ]] || die "Repository not found at $REPO_DIR; set BRAIN_REPO_DIR."
cd "$REPO_DIR"

[[ "$(git branch --show-current)" == "$BRANCH" ]] || die "Switch to $BRANCH yourself first; current branch is $(git branch --show-current)."
git remote get-url "$REMOTE" >/dev/null 2>&1 || die "Remote $REMOTE is not configured."

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_branch="recovery/termux-pre-sync-$stamp"
git branch "$backup_branch" HEAD
printf 'RECOVERY_BRANCH=%s\n' "$backup_branch"

# Preserve tracked and untracked work before attempting any merge.
stash_ref=""
if [[ -n "$(git status --porcelain)" ]]; then
  git stash push --include-untracked -m "Brain safe sync recovery $stamp" >/dev/null
  stash_ref="$(git rev-parse -q --verify refs/stash || true)"
  [[ -n "$stash_ref" ]] || die "Working tree backup failed; no merge attempted."
  printf 'WORKTREE_STASH=%s\n' "$stash_ref"
fi

git fetch "$REMOTE" "$BRANCH"
counts="$(git rev-list --left-right --count "HEAD...$REMOTE/$BRANCH")"
read -r ahead behind <<< "$counts"
printf 'LOCAL_ONLY_COMMITS=%s REMOTE_ONLY_COMMITS=%s\n' "$ahead" "$behind"

if (( behind > 0 )); then
  if (( ahead == 0 )); then
    git merge --ff-only "$REMOTE/$BRANCH"
  else
    # Merge rather than rebase to preserve existing local commit identities.
    if ! git merge --no-edit "$REMOTE/$BRANCH"; then
      git merge --abort || true
      printf 'BLOCKED: merge conflict. Recovery branch %s is preserved. Resolve conflicts manually; no local commits were discarded.\n' "$backup_branch" >&2
      exit 20
    fi
  fi
fi

if [[ -n "$stash_ref" ]]; then
  if ! git stash pop; then
    printf 'BLOCKED: saved work could not be cleanly restored. It remains in the stash; recovery branch=%s stash=%s\n' "$backup_branch" "$stash_ref" >&2
    exit 21
  fi
fi

[[ -f "$SECRET_TOOL" ]] || die "The sync completed, but $SECRET_TOOL is absent from the resulting checkout. Inspect origin history; do not fabricate a replacement."
chmod u+x "$SECRET_TOOL"
printf 'SYNC=SUCCESS\n'
printf 'SECRET_TOOL=%s/%s\n' "$REPO_DIR" "$SECRET_TOOL"
printf 'NEXT: the secret tool will ask for the runner-watch token invisibly and validate it before writing the GitHub Actions secret.\n'

# The original tool refuses empty or invalid tokens and never prints the token.
exec bash "$SECRET_TOOL" "omarenserat1980/MySimpleProject"
