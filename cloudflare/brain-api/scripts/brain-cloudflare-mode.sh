#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${BRAIN_CLOUDFLARE_MODE:-emulator}"
ACTION="${1:-status}"

case "$MODE" in
  emulator|real-readonly|real-deploy) ;;
  *) echo "INVALID_BRAIN_CLOUDFLARE_MODE=$MODE" >&2; exit 2 ;;
esac

echo "BRAIN_CLOUDFLARE_MODE=$MODE"
echo "BRAIN_CLOUDFLARE_ACTION=$ACTION"

case "$ACTION" in
  status)
    if [[ "$MODE" == "emulator" ]]; then
      echo "REAL_CLOUDFLARE_ACCESS=DISABLED_BY_DEFAULT"
      echo "CREDENTIALS_REQUIRED=FALSE"
    else
      echo "REAL_CLOUDFLARE_ACCESS=EXPLICIT_MODE"
      echo "CREDENTIALS_REQUIRED=TRUE"
    fi
    ;;
  test)
    # Static/unit gates are deliberately independent of a live Cloudflare account.
    node --check src/index.js
    node test/cloudflare_deploy_static.test.js
    node test/commercial_worker_static.test.js
    node test/cinema_worker_static.test.js
    echo "BRAIN_CLOUDFLARE_EMULATOR_TESTS=PASS"
    ;;
  dev)
    if [[ "$MODE" != "emulator" ]]; then
      echo "DEV_REQUIRES_BRAIN_CLOUDFLARE_MODE=emulator" >&2
      exit 3
    fi
    exec npx wrangler dev
    ;;
  deploy)
    if [[ "$MODE" != "real-deploy" || "${BRAIN_CLOUDFLARE_REAL:-}" != "1" ]]; then
      echo "REAL_DEPLOY_BLOCKED: set BRAIN_CLOUDFLARE_MODE=real-deploy and BRAIN_CLOUDFLARE_REAL=1 deliberately." >&2
      exit 4
    fi
    : "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is required for explicit real deployment}"
    : "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required for explicit real deployment}"
    exec npx wrangler deploy
    ;;
  *)
    echo "Usage: $0 {status|test|dev|deploy}" >&2
    exit 2
    ;;
esac
