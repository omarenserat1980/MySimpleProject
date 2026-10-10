#!/usr/bin/env bash
set -euo pipefail

# Brain Cloud Executor bootstrap.
# Run ON the Linux x86_64 cloud VM that Brain owns.
# Secrets/tokens are never committed or printed.

REPO="${BRAIN_GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RUNNER_DIR="${BRAIN_RUNNER_DIR:-$HOME/brain-cloud-executor}"
RUNNER_VERSION="${BRAIN_RUNNER_VERSION:-2.337.0}"
RUNNER_ARCH="linux-x64"
EXECUTOR_ID="${BRAIN_CLOUD_EXECUTOR_ID:-brain-cloud-$(hostname)-$(cat /etc/machine-id 2>/dev/null || echo unknown)}"
ATTESTATION_FILE="${BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE:-$HOME/.local/state/brain/cloud-executor-attestation.json}"
TRUST_KEY_FILE="${BRAIN_EXECUTOR_ATTESTATION_PUBLIC_KEY_FILE:-/etc/brain/trust/cloud-executor-attestation-ed25519.pub.b64}"
GATE_TMP="$(mktemp /tmp/brain-cloud-executor-gate.XXXXXX.json)"
trap 'rm -f "$GATE_TMP"' EXIT

[ "${BRAIN_CLOUD_EXECUTOR:-}" = "1" ] || { echo "BRAIN_CLOUD_EXECUTOR=1_REQUIRED"; exit 20; }
[ -n "$EXECUTOR_ID" ] || { echo "BRAIN_CLOUD_EXECUTOR_ID_REQUIRED"; exit 24; }
[ -n "${BRAIN_CLOUD_EXECUTOR_REGISTRY_URL:-}" ] || { echo "CLOUD_EXECUTOR_REGISTRY_URL_REQUIRED"; exit 33; }
[ -n "${BRAIN_CLOUD_EXECUTOR_TOKEN:-}" ] || { echo "CLOUD_EXECUTOR_TOKEN_REQUIRED"; exit 34; }
[ -f "$TRUST_KEY_FILE" ] || { echo "CLOUD_EXECUTOR_ATTESTATION_TRUST_KEY_FILE_MISSING"; exit 26; }
[ ! -L "$TRUST_KEY_FILE" ] || { echo "CLOUD_EXECUTOR_ATTESTATION_TRUST_KEY_SYMLINK_REJECTED"; exit 27; }
[ "$(stat -c %u "$TRUST_KEY_FILE")" = "0" ] || { echo "CLOUD_EXECUTOR_ATTESTATION_TRUST_KEY_NOT_ROOT_OWNED"; exit 28; }
mode="$(stat -c %a "$TRUST_KEY_FILE")"
(( (8#$mode & 0022) == 0 )) || { echo "CLOUD_EXECUTOR_ATTESTATION_TRUST_KEY_WRITABLE_BY_NON_ROOT"; exit 32; }
ATTESTATION_PUBLIC_KEY="$(cat "$TRUST_KEY_FILE")"

command -v gh >/dev/null || { echo "MISSING:gh"; exit 2; }
command -v curl >/dev/null || { echo "MISSING:curl"; exit 2; }
command -v tar >/dev/null || { echo "MISSING:tar"; exit 2; }
command -v python3 >/dev/null || { echo "MISSING:python3"; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "GITHUB_AUTH_REQUIRED"; exit 3; }

arch="$(uname -m)"
[ "$arch" = "x86_64" ] || { echo "CLOUD_EXECUTOR_X86_64_REQUIRED:$arch"; exit 22; }
[ -r /dev/kvm ] && [ -w /dev/kvm ] || { echo "CLOUD_EXECUTOR_KVM_REQUIRED"; exit 23; }
[ -f "$ROOT/brain_v12/brain/cloud_executor_gate.py" ] || {
  echo "BRAIN_REPOSITORY_ROOT_REQUIRED"
  exit 25
}

for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mkfs.vfat mcopy; do
  command -v "$tool" >/dev/null || { echo "MISSING_CLOUD_EXECUTOR_TOOL=$tool"; exit 4; }
done
[ -f "${BRAIN_OVMF_CODE:-/usr/share/OVMF/OVMF_CODE_4M.fd}" ] || {
  echo "MISSING_CLOUD_EXECUTOR_OVMF_CODE"
  exit 5
}

# Fail closed before downloading/configuring/registering a GitHub runner.
export BRAIN_CLOUD_EXECUTOR BRAIN_CLOUD_EXECUTOR_ID
export BRAIN_CLOUD_EXECUTOR_REGISTRY_URL
export BRAIN_CLOUD_EXECUTOR_TOKEN
export BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64="$ATTESTATION_PUBLIC_KEY"
mkdir -p "$(dirname "$ATTESTATION_FILE")"
chmod 700 "$(dirname "$ATTESTATION_FILE")"
python3 "$ROOT/tools/request_cloud_executor_attestation.py" --output "$ATTESTATION_FILE"
export BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE="$ATTESTATION_FILE"
python3 "$ROOT/brain_v12/brain/cloud_executor_gate.py" --output "$GATE_TMP"
python3 - "$GATE_TMP" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    evidence = json.load(f)
if evidence.get("verified") is not True:
    raise SystemExit("CLOUD_EXECUTOR_GATE_BLOCKED")
print("CLOUD_EXECUTOR_PRE_REGISTRATION_GATE=VERIFIED")
print("CLOUD_EXECUTOR_EVIDENCE_REF=" + str(evidence.get("evidence_ref", "")))
PY

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [ ! -x ./run.sh ]; then
  archive="actions-runner-$RUNNER_VERSION-$RUNNER_ARCH.tar.gz"
  curl -fsSL -o "$archive" "https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/$archive"
  tar -xzf "$archive"
  rm -f "$archive"
fi

TOKEN="$(gh api --method POST -H "Accept: application/vnd.github+json" "/repos/$REPO/actions/runners/registration-token" --jq '.token')"
export RUNNER_ALLOW_RUNASROOT=0
./config.sh --unattended \
  --url "https://github.com/$REPO" \
  --token "$TOKEN" \
  --name "$EXECUTOR_ID" \
  --labels "self-hosted,linux,x64,brain-internal,qemu,windows-real-boot,brain-cloud-executor" \
  --work "_work" \
  --ephemeral \
  --replace
unset TOKEN
install -m 600 "$GATE_TMP" "$HOME/.local/state/brain/cloud-executor-gate.json"
rm -f "$ATTESTATION_FILE"
unset BRAIN_CLOUD_EXECUTOR_TOKEN BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64

echo "BRAIN_CLOUD_EXECUTOR_BOOTSTRAP=VERIFIED"
echo "BRAIN_CLOUD_EXECUTOR_ID=$EXECUTOR_ID"
echo "BRAIN_CLOUD_EXECUTOR_MODE=EPHEMERAL_ONE_JOB"
echo "Starting one-job ephemeral runner in the foreground."
exec ./run.sh
