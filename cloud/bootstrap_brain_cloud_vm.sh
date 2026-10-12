#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a user-owned Linux x86_64 VM for Brain Cloud.
# This script prepares Docker and the host packages required by the Brain
# container. It never registers a GitHub Actions runner.

if [[ "$(uname -m)" != "x86_64" && "$(uname -m)" != "amd64" ]]; then
  echo "BRAIN_CLOUD_HOST_ARCH_UNSUPPORTED:$(uname -m)" >&2
  exit 20
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "BRAIN_CLOUD_HOST_OS_UNSUPPORTED:$(uname -s)" >&2
  exit 21
fi

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin qemu-system-x86 qemu-utils ovmf xorriso wimtools dosfstools mtools curl git
  sudo systemctl enable --now docker
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y docker qemu-system-x86 qemu-img edk2-ovmf xorriso wimlib dosfstools mtools curl git
  sudo systemctl enable --now docker
else
  echo "BRAIN_CLOUD_HOST_PACKAGE_MANAGER_UNSUPPORTED" >&2
  exit 22
fi

if ! sudo docker compose version >/dev/null 2>&1; then
  echo "BRAIN_CLOUD_DOCKER_COMPOSE_UNAVAILABLE" >&2
  exit 23
fi

echo "BRAIN_CLOUD_HOST=READY"
echo "BRAIN_CLOUD_DOCKER=READY"
echo "BRAIN_CLOUD_QEMU=READY"
echo "BRAIN_CLOUD_KVM=$([[ -e /dev/kvm ]] && echo AVAILABLE || echo UNAVAILABLE)"
