#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export BRAIN6_168H="1"
export BRAIN_MAX_RUNTIME_SECONDS="604800"
export BRAIN_MAX_ITERATIONS="1000000"
export FACTORY_ONE_SHOT="0"
export FACTORY_ALLOW_PRODUCTION="1"
export FACTORY_ALLOW_LOCAL_FALLBACK="1"
export FACTORY_EMERGENCY_LOCAL_FALLBACK="1"
export FACTORY_REQUIRE_REAL_MEDIA="1"
export FACTORY_MODEL_ROUTER="1"
mkdir -p "$ROOT/runtime/brain6"
exec python3 -m brain_v7.braincore_v2.background_factory_worker
