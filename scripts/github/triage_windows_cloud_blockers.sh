#!/usr/bin/env bash
# One-command, read-only triage for Windows Cloud blockers.
# Runs public endpoint diagnostics and OpenAPI route discovery only.
# Never reads or prints secret values, enrolls nodes, provisions infrastructure, or issues contracts.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
READINESS="$ROOT/scripts/github/check_windows_control_plane_readiness.sh"
DISCOVERY="$ROOT/scripts/github/discover_windows_executor_registry_endpoint.sh"
for tool in "$READINESS" "$DISCOVERY"; do
  [[ -f "$tool" ]] || { printf 'BLOCKED=TOOL_NOT_FOUND:%s\n' "$(basename "$tool")"; exit 2; }
done
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
readiness_rc=0
discovery_rc=0
bash "$READINESS" >"$tmp/readiness.out" 2>&1 || readiness_rc=$?
bash "$DISCOVERY" >"$tmp/discovery.out" 2>&1 || discovery_rc=$?
printf '%s\n' '=== CONTROL PLANE READINESS (safe fields only) ==='
cat "$tmp/readiness.out"
printf 'READINESS_EXIT_CODE=%s\n' "$readiness_rc"
printf '%s\n' '=== PUBLIC OPENAPI ROUTE DISCOVERY ==='
cat "$tmp/discovery.out"
printf 'DISCOVERY_EXIT_CODE=%s\n' "$discovery_rc"
printf '%s\n' '=== NEXT ACTIONS ==='
if grep -q 'CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_PROVIDER: Select and explicitly configure a real supported provider backend; do not enable provisioning without approved credentials and a reviewed plan.'
fi
if grep -q 'SECRETS_READINESS_MISSING_ITEMS=.*fabric_url' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_FABRIC_URL: Obtain the actual HTTPS Brain Fabric endpoint from the authorized service owner; do not assume the Control Plane URL is the Fabric URL.'
fi
if grep -q 'SECRETS_READINESS_MISSING_ITEMS=.*windows_node_id' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_NODE_ID: Assign a stable unique ID to the real Windows guest.'
fi
if grep -q 'SECRETS_READINESS_MISSING_ITEMS=.*enrollment_token' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_ENROLLMENT: After configuring Fabric URL and an authorized control token, issue a short-lived enrollment token and deliver it to the guest over a secure channel.'
fi
if grep -q 'SECRETS_READINESS_MISSING_ITEMS=.*control_auth' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_CONTROL_AUTH: Configure BRAIN_CONTROL_TOKEN or BRAIN_CONTROL_KEY via the authorized secret-management path; never paste it into chat or commit it.'
fi
if grep -q 'CLOUD_STATUS_NODES_COUNT=0' "$tmp/readiness.out"; then
  printf '%s\n' 'ACTION_GUEST_HEARTBEAT: No registered Windows guest is currently reporting; enrollment and a fresh authenticated heartbeat are still required.'
fi
printf '%s\n' 'FINAL=NOT_VERIFIED'
printf '%s\n' 'NOTE=This triage is read-only. It does not provision a VM, create credentials, issue contracts, or prove guest boot.'
[[ "$readiness_rc" -eq 0 && "$discovery_rc" -eq 0 ]]
