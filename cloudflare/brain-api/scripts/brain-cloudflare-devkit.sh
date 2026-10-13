#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${BRAIN_CLOUDFLARE_MODE:-emulator}"
ACTION="${1:-help}"
PROMPTS_FILE="$(cd "$ROOT/../.." && pwd)/docs/prompts/CHATGPT_CLOUDFLARE_EMULATOR_PROMPTS_AR.md"

show_help() {
  cat <<'HELP'
Brain Cloudflare DevKit (emulator-first; no cloud credentials needed)

Usage:
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh status
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh doctor
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh test
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh dev
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh prompts
  bash cloudflare/brain-api/scripts/brain-cloudflare-devkit.sh deploy

Commands:
  status   Show selected mode and whether live access is enabled.
  doctor   Check local prerequisites without printing secret values.
  test     Run isolated static/emulator gates without Cloudflare credentials.
  dev      Start Wrangler local development mode.
  prompts  Print Arabic ChatGPT prompt templates for emulator development.
  deploy   Refuse unless real deployment is explicitly opted into.

Default mode is emulator. This tool never enables R2, creates cloud resources,
or deploys to a live account automatically.
HELP
}

case "$ACTION" in
  help|-h|--help)
    show_help
    ;;
  status)
    bash scripts/brain-cloudflare-mode.sh status
    printf 'DEVKIT=READY\n'
    ;;
  doctor)
    printf 'BRAIN_CLOUDFLARE_MODE=%s\n' "$MODE"
    missing=0
    for cmd in bash node npx; do
      if command -v "$cmd" >/dev/null 2>&1; then
        printf '%s=FOUND\n' "$cmd"
      else
        printf '%s=MISSING\n' "$cmd"
        missing=1
      fi
    done
    if [[ -f wrangler.toml ]]; then printf 'WRANGLER_CONFIG=FOUND\n'; else printf 'WRANGLER_CONFIG=MISSING\n'; missing=1; fi
    if [[ -f src/index.js ]]; then printf 'WORKER_ENTRY=FOUND\n'; else printf 'WORKER_ENTRY=MISSING\n'; missing=1; fi
    if [[ "$MODE" == "emulator" ]]; then
      printf 'CLOUD_CREDENTIALS_REQUIRED=FALSE\n'
    else
      printf 'CLOUD_CREDENTIALS_REQUIRED=TRUE_FOR_REAL_MODE\n'
    fi
    exit "$missing"
    ;;
  test)
    [[ "$MODE" == "emulator" ]] || { echo "TEST_BLOCKED: set BRAIN_CLOUDFLARE_MODE=emulator for isolated tests" >&2; exit 3; }
    bash -n scripts/brain-cloudflare-mode.sh
    bash -n scripts/brain-cloudflare-devkit.sh
    node --check src/index.js
    node test/cloudflare_deploy_static.test.js
    node test/commercial_worker_static.test.js
    node test/cinema_worker_static.test.js
    node test/devkit_static.test.js
    printf 'BRAIN_CLOUDFLARE_DEVKIT_TESTS=PASS\nLIVE_CLOUDFLARE_USED=FALSE\n'
    ;;
  dev)
    [[ "$MODE" == "emulator" ]] || { echo "DEV_BLOCKED: local dev requires emulator mode" >&2; exit 3; }
    exec bash scripts/brain-cloudflare-mode.sh dev
    ;;
  prompts)
    [[ -f "$PROMPTS_FILE" ]] || { echo "PROMPTS_FILE_NOT_FOUND=$PROMPTS_FILE" >&2; exit 5; }
    cat "$PROMPTS_FILE"
    ;;
  deploy)
    # Delegates to the existing explicit opt-in gate; never changes mode silently.
    exec bash scripts/brain-cloudflare-mode.sh deploy
    ;;
  *)
    echo "Unknown command: $ACTION" >&2
    show_help >&2
    exit 2
    ;;
esac
