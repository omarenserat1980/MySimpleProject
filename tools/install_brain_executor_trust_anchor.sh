#!/usr/bin/env bash
set -euo pipefail
# Install PUBLIC key material from an independent trusted host-management channel.
# Confirm the expected SHA-256 fingerprint through a separate channel.
DEST="${BRAIN_EXECUTOR_ATTESTATION_PUBLIC_KEY_FILE:-/etc/brain/trust/cloud-executor-attestation-ed25519.pub.b64}"
EXPECTED="${BRAIN_TRUST_ANCHOR_SHA256:-}"
[ -n "$EXPECTED" ] || { echo "BRAIN_TRUST_ANCHOR_SHA256_REQUIRED_FROM_INDEPENDENT_CHANNEL"; exit 20; }
[[ "$EXPECTED" =~ ^[A-Fa-f0-9]{64}$ ]] || { echo "BRAIN_TRUST_ANCHOR_SHA256_INVALID"; exit 21; }
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
cat > "$tmp"
tr -d '\r\n ' < "$tmp" | base64 -d >/dev/null || { echo "TRUST_ANCHOR_BASE64_INVALID"; exit 22; }
actual="$(tr -d '\r\n ' < "$tmp" | base64 -d | sha256sum | awk '{print $1}')"
[ "${actual,,}" = "${EXPECTED,,}" ] || { echo "TRUST_ANCHOR_FINGERPRINT_MISMATCH"; exit 23; }
install -d -o root -g root -m 0755 "$(dirname "$DEST")"
install -o root -g root -m 0644 "$tmp" "$DEST"
printf 'TRUST_ANCHOR_INSTALLED path=%s sha256=%s\n' "$DEST" "$actual"
