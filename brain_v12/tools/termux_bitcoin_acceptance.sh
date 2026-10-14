#!/data/data/com.termux/files/usr/bin/bash
# Electronic Brain: Termux Bitcoin SHA-256d acceptance preflight.
# Safe by default: this script does NOT start mining or contact a pool.
set -u
ROOT="${BRAIN_REPO_ROOT:-$HOME/MySimpleProject}"
OUT="${BRAIN_MINING_EVIDENCE_DIR:-$HOME/brain-mining-evidence}"
mkdir -p "$OUT"
REPORT="$OUT/termux-preflight-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec > >(tee "$REPORT") 2>&1

echo "component=electronic-brain-termux-bitcoin-preflight"
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "device_arch=$(uname -m 2>/dev/null || echo unknown)"
echo "android_abis=$(getprop ro.product.cpu.abilist 2>/dev/null || echo unavailable)"
echo "termux_version=${TERMUX_VERSION:-unset}"
echo "python=$(python --version 2>&1 || true)"
echo "git=$(git --version 2>&1 || true)"
echo "clang=$(clang --version 2>/dev/null | head -n 1 || echo unavailable)"
echo "make=$(make --version 2>/dev/null | head -n 1 || echo unavailable)"
MINER_PATH="$(command -v cpuminer || true)"
echo "cpuminer_path=${MINER_PATH:-not-installed}"

if [ ! -d "$ROOT/.git" ]; then
  echo "status=BLOCKED_REPOSITORY_NOT_FOUND"
  echo "expected_repo=$ROOT"
  echo "No mining process started."
  exit 2
fi

cd "$ROOT" || exit 2
echo "repo_root=$ROOT"
echo "git_branch=$(git branch --show-current)"
echo "git_commit=$(git rev-parse HEAD)"
echo "git_worktree_status_begin"
git status --short
echo "git_worktree_status_end"

if ! python -c 'import brain_v12.brain.termux_bitcoin_worker' >/dev/null 2>&1; then
  echo "status=BLOCKED_WORKER_IMPORT_FAILED"
  echo "No mining process started."
  exit 2
fi

echo "unit_tests_begin"
if python -m unittest brain_v12.tests.test_termux_bitcoin_worker -v; then
  echo "unit_tests=PASS"
else
  echo "unit_tests=FAIL"
  echo "No mining process started."
  exit 1
fi
echo "unit_tests_end"

if [ -n "$MINER_PATH" ]; then
  echo "miner_version_begin"
  cpuminer --version 2>&1 | head -n 8 || true
  echo "miner_version_end"

  if command -v file >/dev/null 2>&1; then
    echo "miner_file_type=$(file "$MINER_PATH" 2>&1 | head -n 1)"
  else
    echo "miner_file_type=UNAVAILABLE_FILE_COMMAND_NOT_INSTALLED"
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    echo "miner_sha256=$(sha256sum "$MINER_PATH" 2>/dev/null | awk '{print $1}' || true)"
  else
    echo "miner_sha256=UNAVAILABLE_SHA256SUM_NOT_INSTALLED"
  fi

  MINER_HELP="$(cpuminer --help 2>&1 || true)"
  if printf '%s\n' "$MINER_HELP" | grep -Eiq 'sha256d|sha-256d|sha256'; then
    echo "miner_sha256d_help_signal=FOUND_UNVERIFIED"
  else
    echo "miner_sha256d_help_signal=NOT_FOUND_OR_HELP_UNAVAILABLE"
  fi
  if printf '%s\n' "$MINER_HELP" | grep -Eiq 'stratum| -o([ ,]|$)'; then
    echo "miner_stratum_help_signal=FOUND_UNVERIFIED"
  else
    echo "miner_stratum_help_signal=NOT_FOUND_OR_HELP_UNAVAILABLE"
  fi
  echo "miner_binary_provenance=NOT_VERIFIED"
  echo "miner_algorithm_support=NOT_VERIFIED; help text and local checksum are clues only, compare checksum to publisher's trusted release"
else
  echo "miner_status=NOT_INSTALLED"
  echo "miner_file_type=NOT_APPLICABLE"
  echo "miner_sha256=NOT_APPLICABLE"
  echo "miner_sha256d_help_signal=NOT_APPLICABLE"
  echo "miner_stratum_help_signal=NOT_APPLICABLE"
fi

echo "status=PREFLIGHT_COMPLETE_NOT_MINING"
echo "pool_session_verified=false"
echo "pool_side_hashrate_verified=false"
echo "accepted_shares_verified=false"
echo "revenue_verified=false"
echo "evidence_report=$REPORT"
echo "No mining process was started and no pool was contacted."
echo "Next: verify the binary source and checksum against a trusted publisher release, then separately verify pool-side session, hashrate, shares, and payout. Never put pool passwords or wallet secrets in this report."
