#!/usr/bin/env bash
# Cloudflare R2 preflight for Brain Cinema.
# Run from repository root: bash cloudflare/brain-api/scripts/r2-preflight.sh
set -Eeuo pipefail

fail() { printf 'R2_PREFLIGHT=FAIL\n%s\n' "$*" >&2; exit 1; }

command -v npx >/dev/null 2>&1 || fail "Node.js/npm are required (npx was not found)."
[[ -n "${CLOUDFLARE_API_TOKEN:-}" ]] || fail "Set CLOUDFLARE_API_TOKEN in the environment; do not paste it into chat or commit it."
[[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]] || fail "Set CLOUDFLARE_ACCOUNT_ID in the environment."

cd "$(dirname "$0")/.."
printf 'Checking Wrangler authentication...\n'
if ! npx --yes wrangler whoami; then
  fail "Wrangler authentication failed. Verify token validity and account access."
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
printf 'Checking whether R2 is enabled and listing buckets...\n'
if ! npx --yes wrangler r2 bucket list >"$tmp" 2>&1; then
  cat "$tmp" >&2
  if grep -q '10042' "$tmp"; then
    fail "Cloudflare reports R2 is not enabled for this account. Enable R2 in the Cloudflare Dashboard first, then rerun this script."
  fi
  fail "R2 bucket listing failed. Check the diagnostic above and confirm the API token has R2 read/write access."
fi
cat "$tmp"
if ! grep -Fq 'brain-cinema-media' "$tmp"; then
  printf 'Creating required private cinema bucket...\n'
  npx --yes wrangler r2 bucket create brain-cinema-media
fi
npx --yes wrangler r2 bucket list | grep -Fq 'brain-cinema-media' || fail "Bucket brain-cinema-media was not found after the create/list check."
printf 'R2_PREFLIGHT=PASS\nCINEMA_R2_BUCKET_READY=TRUE\n'
