#!/usr/bin/env bash
set -uo pipefail
REPO="${BRAIN_GITHUB_REPO:-omarenserat1980/MySimpleProject}"
URL="${V12_BRAIN_URL:-${BRAIN_URL:-http://127.0.0.1:8012}}"
DIR="${BRAIN_EVIDENCE_DIR:-$HOME/.brain/recovery-evidence}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$DIR/brain-diagnostics-$STAMP.txt"
mkdir -p "$DIR" || exit 2
umask 077
{
 echo "Electronic Brain diagnostic evidence"; echo "utc_time=$STAMP"; echo "repository=$REPO"; echo "brain_url=$URL"; echo "mode=read-only; no remote commands or VM changes"
 echo; echo "=== HOST ==="; uname -a; df -h "$HOME"; (free -h 2>/dev/null || true)
 echo; echo "=== LOCAL PROCESSES ==="; ps -ef | grep -E "[u]vicorn|[b]rain_runtime|[t]ermux-agent|[a]ctions.runner" || true
 echo; echo "=== CONFIG PRESENCE ONLY ==="
 for f in "$HOME/.brain_env" "$HOME/v12-agent/agent_config.sh"; do if [ -f "$f" ]; then echo "$f=present"; else echo "$f=missing"; fi; done
 for endpoint in /api/system/readiness /api/media/health /api/cinema/status; do
  echo; echo "=== HTTP $endpoint ==="
  if command -v curl >/dev/null 2>&1; then
   curl --silent --show-error --max-time 5 --output /tmp/brain-diag-body.$$ --write-out 'http_status=%{http_code} seconds=%{time_total}\n' "${URL%/}$endpoint" || true
   if [ -f /tmp/brain-diag-body.$$ ]; then head -c 1000 /tmp/brain-diag-body.$$; echo; rm -f /tmp/brain-diag-body.$$; fi
  else echo "CURL_NOT_INSTALLED"; fi
 done
 echo; echo "=== GITHUB ACTIONS RECENT RUNS ==="
 if command -v curl >/dev/null 2>&1; then
  api="https://api.github.com/repos/$REPO/actions/runs?per_page=20"
  if [ -n "${GH_TOKEN:-}" ]; then
   curl -fsS --max-time 12 -H "Authorization: Bearer $GH_TOKEN" -H 'Accept: application/vnd.github+json' "$api" |
    python -c 'import json,sys; d=json.load(sys.stdin); [print("{} | {} | {} | {}".format(r.get("name"),r.get("status"),r.get("conclusion"),r.get("html_url"))) for r in d.get("workflow_runs",[])]' || echo "GITHUB_API_FAILED"
  else
   curl -fsS --max-time 12 -H 'Accept: application/vnd.github+json' "$api" |
    python -c 'import json,sys; d=json.load(sys.stdin); [print("{} | {} | {} | {}".format(r.get("name"),r.get("status"),r.get("conclusion"),r.get("html_url"))) for r in d.get("workflow_runs",[])]' || echo "GITHUB_API_FAILED"
  fi
 else echo "CURL_NOT_INSTALLED"; fi
 echo; echo "=== NEXT ACTIONS ==="
 echo "Use gh run view RUN_ID --log-failed after gh auth login for failed-job logs."
 echo "Run arkan_runtime_recovery.ps1 on Windows for Hyper-V and runner evidence."
 echo "A Running VM state does not prove Windows boot/login."
 echo "Never share .env files, private keys, runner tokens, or control keys."
} 2>&1 | sed -E 's/(gh[pousr]_[A-Za-z0-9_]{20,})/[REDACTED_GITHUB_TOKEN]/g' | tee "$OUT"
echo "EVIDENCE_PATH=$OUT"