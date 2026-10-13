#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="$ROOT/.wrangler.emulator.generated.toml"
DATA_DIR="${TMPDIR:-/tmp}/brain-wrangler-emulator-$$"
LOG="${TMPDIR:-/tmp}/brain-wrangler-emulator-$$.log"
PORT="${BRAIN_EMULATOR_PORT:-18787}"
PID=""

cleanup() {
  if [[ -n "$PID" ]]; then kill "$PID" >/dev/null 2>&1 || true; wait "$PID" 2>/dev/null || true; fi
  rm -f "$CONFIG"
  rm -rf "$DATA_DIR"
  rm -f "$LOG"
}
trap cleanup EXIT

cat > "$CONFIG" <<'TOML'
name = "brain-cloud-api-emulator-smoke"
main = "src/index.js"
compatibility_date = "2026-10-02"

[vars]
BRAIN_ALLOWED_ORIGIN = "http://127.0.0.1:18787"

[[d1_databases]]
binding = "BRAIN_DB"
database_name = "brain-commercial-emulator"
database_id = "00000000-0000-0000-0000-000000000001"
migrations_dir = "migrations"

[[r2_buckets]]
binding = "CINEMA_MEDIA"
bucket_name = "brain-cinema-media-emulator"
TOML

mkdir -p "$DATA_DIR"
npx --yes wrangler@4 dev --local --ip 127.0.0.1 --port "$PORT" --config "$CONFIG" --persist-to "$DATA_DIR" >"$LOG" 2>&1 &
PID=$!

ready=0
for _ in $(seq 1 45); do
  if curl --silent --show-error --fail "http://127.0.0.1:$PORT/health" > "$DATA_DIR/health.json" 2>/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "WRANGLER_EXITED_BEFORE_HEALTH" >&2
    cat "$LOG" >&2
    exit 1
  fi
  sleep 2
done

if [[ "$ready" != "1" ]]; then
  echo "WRANGLER_HEALTH_TIMEOUT" >&2
  cat "$LOG" >&2
  exit 1
fi

node --input-type=module - "$DATA_DIR/health.json" <<'NODE'
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const payload = JSON.parse(readFileSync(process.argv[2], "utf8"));
assert.equal(payload.ok, true);
assert.equal(payload.service, "brain-cloud-api");
assert.equal(payload.mode, "commercial-edge");
assert.equal(payload.d1, "CONFIGURED");
console.log("BRAIN_WRANGLER_LOCAL_HEALTH=PASS");
console.log("LIVE_CLOUDFLARE_USED=FALSE");
console.log(JSON.stringify(payload));
NODE
