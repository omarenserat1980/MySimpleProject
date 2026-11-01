#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="omarenserat1980/MySimpleProject"
OWNER="omarenserat1980"
TARGET_BRANCH="brain/honda-android-network-sqlite"
ACTION="${1:-status}"
[ -n "$ACTION" ] || ACTION="status"

fail() {
  printf 'BRAIN GitHub Bridge: %s\n' "$1" >&2
  exit 1
}

select_owner() {
  gh auth switch --hostname github.com --user "$OWNER" >/dev/null
  gh auth setup-git --hostname github.com
}

verify_access() {
  command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) is not installed."
  local login
  login="$(gh api user --jq .login)"
  [ "$login" = "$OWNER" ] || fail "Active GitHub identity is '$login', expected '$OWNER'. Run: $0 select-owner"

  local access
  access="$(gh api "repos/$REPOSITORY" --jq '[.permissions.admin, .permissions.push] | @tsv')"
  case "$access" in
    "true	true"|"true	false"|"false	true") ;;
    *) fail "Repository write access is not confirmed. Check the GitHub account/repository permissions." ;;
  esac
  printf 'Authenticated account: %s\nRepository: %s\nAdmin/push permissions: %s\n' "$login" "$REPOSITORY" "$access"
}

case "$ACTION" in
  select-owner)
    select_owner
    verify_access
    ;;
  status)
    verify_access
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      printf 'Current branch: %s\n' "$(git branch --show-current)"
      git status --short
    else
      printf 'Not inside a Git worktree.\n'
    fi
    ;;
  push)
    verify_access
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Run this inside the repository worktree."
    current="$(git branch --show-current)"
    [ "$current" = "$TARGET_BRANCH" ] || fail "Refusing to push branch '$current'. Only '$TARGET_BRANCH' is allowed."
    [ -z "$(git status --porcelain)" ] || fail "Working tree is not clean. Review and commit changes before pushing."
    git push -u origin "HEAD:refs/heads/$TARGET_BRANCH"
    ;;
  *)
    printf 'Usage: %s {status|select-owner|push}\n' "$0"
    exit 2
    ;;
esac
