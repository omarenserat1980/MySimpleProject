#!/usr/bin/env bash
set -euo pipefail

# Brain-owned self-hosted runner bootstrap.
# Run this ON THE USER-OWNED Linux x64 host that will execute Brain workloads.
# No runner registration token is stored in Git or printed.

REPO="${BRAIN_GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
RUNNER_DIR="${BRAIN_RUNNER_DIR:-$HOME/brain-internal-runner}"
RUNNER_VERSION="${BRAIN_RUNNER_VERSION:-2.329.0}"
LABELS="self-hosted,linux,x64,brain-internal,qemu,windows-real-boot"
RUNNER_ARCH="linux-x64"

command -v gh >/dev/null || { echo "MISSING:gh"; exit 2; }
command -v curl >/dev/null || { echo "MISSING:curl"; exit 2; }
command -v tar >/dev/null || { echo "MISSING:tar"; exit 2; }

if ! gh auth status >/dev/null 2>&1; then
  echo "GITHUB_AUTH_REQUIRED"
  exit 3
fi

for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mkfs.vfat mcopy; do
  command -v "$tool" >/dev/null || { echo "MISSING_INTERNAL_RUNNER_TOOL=$tool"; exit 4; }
done

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -x ./run.sh ]; then
  archive="actions-runner-$RUNNER_VERSION-$RUNNER_ARCH.tar.gz"
  curl -fsSL -o "$archive" \
    "https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/$archive"
  tar -xzf "$archive"
  rm -f "$archive"
fi

export RUNNER_ALLOW_RUNASROOT=0
export BRAIN_INTERNAL_RUNNER_FLAG=1

TOKEN="$(gh api --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/actions/runners/registration-token" \
  --jq '.token')"

./config.sh --unattended \
  --url "https://github.com/$REPO" \
  --token "$TOKEN" \
  --name "${BRAIN_INTERNAL_RUNNER_ID:-linux-runner-01}" \
  --labels "$LABELS" \
  --work "_work" \
  --replace

unset TOKEN

cat > .env <<'EOF'
BRAIN_INTERNAL_RUNNER_FLAG=1
BRAIN_INTERNAL_RUNNER_LABELS=self-hosted,linux,x64,brain-internal,qemu,windows-real-boot
EOF
chmod 600 .env

./svc.sh install
./svc.sh start

echo "BRAIN_INTERNAL_RUNNER_BOOTSTRAP=STARTED"
echo "RUNNER_LABELS=$LABELS"
echo "RUNNER_DIR=$RUNNER_DIR"
