#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Brain Runtime Source Manager
# Purpose: keep the running runtime converged with origin/main without
# touching the user's active development branch or working tree.

SOURCE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_ROOT="${BRAIN_RUNTIME_ROOT:-$HOME/.brain/runtime}"
REMOTE="${BRAIN_RUNTIME_REMOTE:-origin}"
REF="${BRAIN_RUNTIME_REF:-main}"

mkdir -p "$(dirname "$RUNTIME_ROOT")"

if ! command -v git >/dev/null 2>&1; then
  echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=GIT_NOT_FOUND" >&2
  exit 50
fi

cd "$SOURCE_ROOT"

# Fetch only the source ref. This never merges or modifies the active branch.
git fetch "$REMOTE" "$REF" >/dev/null 2>&1 || {
  echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=FETCH_FAILED" >&2
  exit 51
}

EXPECTED="$(git rev-parse "$REMOTE/$REF")"

# Git worktrees use a .git *file*, not a .git directory. Detect a worktree
# through Git itself. Never rm -rf the runtime path: it may contain state or
# user data if it is not the expected worktree.
if git -C "$RUNTIME_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$RUNTIME_ROOT" reset --hard "$EXPECTED" >/dev/null
else
  if [ -e "$RUNTIME_ROOT" ]; then
    if [ ! -d "$RUNTIME_ROOT" ]; then
      echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=RUNTIME_PATH_EXISTS_NOT_DIRECTORY path=$RUNTIME_ROOT" >&2
      exit 54
    fi
    if ! rmdir "$RUNTIME_ROOT" 2>/dev/null; then
      echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=RUNTIME_PATH_EXISTS_NOT_WORKTREE path=$RUNTIME_ROOT; preserved_existing_contents=1" >&2
      exit 55
    fi
  fi
  git worktree add --detach "$RUNTIME_ROOT" "$EXPECTED" >/dev/null || {
    echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=WORKTREE_ADD_FAILED path=$RUNTIME_ROOT" >&2
    exit 56
  }
fi

ACTUAL="$(git -C "$RUNTIME_ROOT" rev-parse HEAD)"
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=COMMIT_MISMATCH expected=$EXPECTED actual=$ACTUAL" >&2
  exit 52
fi

if ! grep -q '/api/brain/life-certificate' "$RUNTIME_ROOT/brain_v12/app.py"; then
  echo "BRAIN_RUNTIME_CONVERGENCE_ERROR=TRUTH_GATE_MISSING commit=$ACTUAL" >&2
  exit 53
fi

cat > "$RUNTIME_ROOT/.brain-runtime-identity" <<EOF
node_id=${V12_AGENT_ID:-redmi3-01}
runtime_commit=$ACTUAL
expected_commit=$EXPECTED
source_ref=$REMOTE/$REF
runtime_root=$RUNTIME_ROOT
EOF

echo "BRAIN_RUNTIME_CONVERGED=1"
echo "BRAIN_RUNTIME_ROOT=$RUNTIME_ROOT"
echo "BRAIN_RUNTIME_COMMIT=$ACTUAL"
echo "BRAIN_RUNTIME_EXPECTED=$EXPECTED"
