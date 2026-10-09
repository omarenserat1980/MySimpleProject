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
ATTESTATION_B64="${BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64:-}"
ATTESTATION_PUBLIC_KEY_B64="${BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64:-}"

[ "${BRAIN_CLOUD_EXECUTOR:-}" = "1" ] || { echo "BRAIN_CLOUD_EXECUTOR=1_REQUIRED"; exit 20; }
[ -n "$ATTESTATION_B64" ] || { echo "BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64_REQUIRED"; exit 21; }
[ -n "$ATTESTATION_PUBLIC_KEY_B64" ] || { echo "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_REQUIRED"; exit 24; }

# The runner is configured as the invoking user, while its systemd service is
# installed through sudo. Keep the EnvironmentFile path systemd-safe and stable.
mkdir -p "$RUNNER_DIR"
RUNNER_DIR="$(cd "$RUNNER_DIR" && pwd -P)"
[[ "$RUNNER_DIR" =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "UNSUPPORTED_RUNNER_DIR_FOR_SYSTEMD"; exit 25; }
[[ "$EXECUTOR_ID" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "INVALID_CLOUD_EXECUTOR_ID"; exit 26; }
[[ "$ATTESTATION_B64" =~ ^[A-Za-z0-9+/]+={0,2}$ ]] || { echo "INVALID_CLOUD_EXECUTOR_ATTESTATION_B64"; exit 27; }
[[ "$ATTESTATION_PUBLIC_KEY_B64" =~ ^[A-Za-z0-9+/]+={0,2}$ ]] || { echo "INVALID_CLOUD_EXECUTOR_PUBLIC_KEY_B64"; exit 28; }

command -v gh >/dev/null || { echo "MISSING:gh"; exit 2; }
command -v curl >/dev/null || { echo "MISSING:curl"; exit 2; }
command -v tar >/dev/null || { echo "MISSING:tar"; exit 2; }
command -v sudo >/dev/null || { echo "MISSING:sudo"; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "GITHUB_AUTH_REQUIRED"; exit 3; }

arch="$(uname -m)"
[ "$arch" = "x86_64" ] || { echo "CLOUD_EXECUTOR_X86_64_REQUIRED:$arch"; exit 22; }
[ -r /dev/kvm ] && [ -w /dev/kvm ] || { echo "CLOUD_EXECUTOR_KVM_REQUIRED"; exit 23; }

for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mkfs.vfat mcopy; do
  command -v "$tool" >/dev/null || { echo "MISSING_CLOUD_EXECUTOR_TOOL=$tool"; exit 4; }
done

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
# Ephemeral registration limits this attestation to a single job. If it expires
# while the runner waits in queue, the security gate fails closed and provisioning
# must issue a fresh attestation before retrying.
./config.sh --unattended --ephemeral --url "https://github.com/$REPO" --token "$TOKEN" --name "$EXECUTOR_ID" --labels "self-hosted,linux,x64,brain-internal,qemu,windows-real-boot,brain-cloud-executor" --work "_work" --replace
unset TOKEN

sed -i \
  -e '/^BRAIN_CLOUD_EXECUTOR=/d' \
  -e '/^BRAIN_CLOUD_EXECUTOR_ID=/d' \
  -e '/^BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64=/d' \
  -e '/^BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64=/d' \
  -e '/^BRAIN_INTERNAL_RUNNER_FLAG=/d' \
  .env
cat >> .env <<EOF
BRAIN_CLOUD_EXECUTOR=1
BRAIN_CLOUD_EXECUTOR_ID=$EXECUTOR_ID
BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64=$ATTESTATION_B64
BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64=$ATTESTATION_PUBLIC_KEY_B64
BRAIN_INTERNAL_RUNNER_FLAG=1
EOF
chmod 600 .env

# Prove the substrate before the service is allowed to become available.
cd "$ROOT"
export BRAIN_CLOUD_EXECUTOR BRAIN_CLOUD_EXECUTOR_ID BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64 BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64
python3 brain_v12/brain/cloud_executor_gate.py --output "$RUNNER_DIR/cloud-executor-gate.json"
grep -q '"verified": true' "$RUNNER_DIR/cloud-executor-gate.json"

cd "$RUNNER_DIR"
SERVICE_USER="$(id -un)"
sudo -n ./svc.sh install "$SERVICE_USER"

# systemd starts runsvc.sh with a clean service environment; the variables
# exported above only reach this bootstrap process. Attach the protected runner
# .env file to the generated unit so the gate sees the same identity at job time.
SERVICE_UNIT="$(cat .service 2>/dev/null || true)"
[[ "$SERVICE_UNIT" =~ ^actions\.runner\.[A-Za-z0-9._-]+\.service$ ]] || {
  echo "CLOUD_EXECUTOR_SYSTEMD_UNIT_NOT_FOUND"
  exit 29
}
DROPIN_DIR="/etc/systemd/system/${SERVICE_UNIT}.d"
DROPIN_TMP="$(mktemp)"
trap 'rm -f "$DROPIN_TMP"' EXIT
printf '[Service]\nEnvironmentFile=%s/.env\n' "$RUNNER_DIR" > "$DROPIN_TMP"
sudo -n install -d -m 0755 "$DROPIN_DIR"
sudo -n install -m 0644 "$DROPIN_TMP" "$DROPIN_DIR/brain-cloud-executor.conf"
sudo -n systemctl daemon-reload
sudo -n ./svc.sh start

echo "BRAIN_CLOUD_EXECUTOR_BOOTSTRAP=VERIFIED"
echo "BRAIN_CLOUD_EXECUTOR_ID=$EXECUTOR_ID"
echo "BRAIN_CLOUD_EXECUTOR_GATE=$RUNNER_DIR/cloud-executor-gate.json"
