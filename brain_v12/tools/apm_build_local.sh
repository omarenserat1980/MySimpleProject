#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "APM_BUILD_LOCAL=START"
python -m compileall -q brain_v12/brain brain_v12/tests
python -m unittest \
  brain_v12.tests.test_parallel_stage_scheduler \
  brain_v12.tests.test_apm_build \
  brain_v12.tests.test_apm_stage_discovery \
  brain_v12.tests.test_apm_profiles \
  brain_v12.tests.test_apm_media_adapter \
  brain_v12.tests.test_apm_media_executor \
  brain_v12.tests.test_apm_chunk_scheduler \
  brain_v12.tests.test_film_segment_manager \
  brain_v12.tests.test_apm_film_assembly \
  brain_v12.tests.test_apm_cinematic_adapter \
  brain_v12.tests.test_apm_film_media_executor \
  -v

mkdir -p brain-artifacts
printf '%s\n' "APM_BUILD_VERIFIED_LOCAL" > brain-artifacts/APM_BUILD_VERIFIED_LOCAL.txt
echo "APM_BUILD_LOCAL=VERIFIED"
