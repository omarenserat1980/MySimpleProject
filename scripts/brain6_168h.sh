#!/usr/bin/env bash
set -euo pipefail

# This compatibility path is intentionally non-executable. Do not route work to
# the retired brain_v7 factory worker through this historical Brain 6 launcher.
echo "BRAIN6_RETIRED: legacy execution is disabled; no worker was started." >&2
echo "Canonical Brain runtime: python3 -m brain_v12.app" >&2
exit 78
