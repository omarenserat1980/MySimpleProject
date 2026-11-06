#!/usr/bin/env bash
set -euo pipefail

EXPECTED_BRANCH="brain/honda-android-network-sqlite"
EXPECTED_UPSTREAM="b3cc871f7c5c4b41947a3c512caee76624eaffd9"
REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"

if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  echo "ERROR: expected branch '$EXPECTED_BRANCH', found '$CURRENT_BRANCH'." >&2
  exit 2
fi

STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
# The integration package itself is expected to be untracked before first run.
# Refuse all other changes so the script cannot mix unrelated user work.
UNEXPECTED="$(printf '%s\n' "$STATUS" | grep -v '^?? android_executor/carlife-md/' | grep -v '^$' || true)"
if [[ -n "$UNEXPECTED" ]]; then
  echo "ERROR: unrelated working-tree changes detected:" >&2
  printf '%s\\n' "$UNEXPECTED" >&2
  exit 3
fi

SUBMODULE_PATH="android_executor/carlife-md/upstream"
PATCH_PATH="$REPO_ROOT/android_executor/carlife-md/patches/0001-fix-ctrl-channel-receive.patch"

if [[ ! -f "$PATCH_PATH" ]]; then
  echo "ERROR: patch file missing: $PATCH_PATH" >&2
  exit 4
fi

mkdir -p "$(dirname "$SUBMODULE_PATH")"
if [[ ! -e "$SUBMODULE_PATH/.git" ]]; then
  git -C "$REPO_ROOT" submodule add https://github.com/Doris-duo/CarLife-MD-Lib.git "$SUBMODULE_PATH"
fi

git -C "$SUBMODULE_PATH" fetch origin "$EXPECTED_UPSTREAM"
git -C "$SUBMODULE_PATH" checkout --detach "$EXPECTED_UPSTREAM"

ACTUAL_UPSTREAM="$(git -C "$SUBMODULE_PATH" rev-parse HEAD)"
if [[ "$ACTUAL_UPSTREAM" != "$EXPECTED_UPSTREAM" ]]; then
  echo "ERROR: upstream source pin mismatch: $ACTUAL_UPSTREAM" >&2
  exit 5
fi

git -C "$SUBMODULE_PATH" apply --check "$PATCH_PATH"
git -C "$SUBMODULE_PATH" apply "$PATCH_PATH"

echo
echo "CTRL receive patch applied to pinned CarLife-MD-Lib source."
echo "Pinned upstream: $ACTUAL_UPSTREAM"
echo "Submodule path: $SUBMODULE_PATH"
echo
echo "Next: inspect 'git -C \"$SUBMODULE_PATH\" diff', then run native tests/build."
echo "No APK has been built and no device/vehicle test has been performed."
