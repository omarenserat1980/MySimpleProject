#!/usr/bin/env bash
# Read-only local preflight for the two supported Windows Cloud provider adapters.
# Never prints secret values and never runs terraform init/plan/apply or OpenNebula mutations.
set -Eeuo pipefail
provider="${BRAIN_WINDOWS_CLOUD_PROVIDER:-}"
printf 'PROVIDER_CONFIGURED=%s\n' "$([[ -n "$provider" ]] && printf true || printf false)"
if [[ -z "$provider" || "$provider" == "none" || "$provider" == "disabled" ]]; then
  printf '%s\n' 'PROVIDER_STATUS=NOT_CONFIGURED'
  printf '%s\n' 'SUPPORTED_BACKENDS=terraform,opennebula'
  printf '%s\n' 'NEXT=Choose a real approved backend and configure its non-secret settings and credentials through the authorized environment.'
  exit 4
fi
case "$provider" in
  terraform)
    root="${BRAIN_WINDOWS_TERRAFORM_DIR:-}"
    bin="${BRAIN_WINDOWS_TERRAFORM_BIN:-terraform}"
    printf 'TERRAFORM_ROOT_CONFIGURED=%s\n' "$([[ -n "$root" && -d "$root" ]] && printf true || printf false)"
    if command -v "$bin" >/dev/null 2>&1 || [[ -x "$bin" ]]; then
      printf '%s\n' 'TERRAFORM_BINARY_AVAILABLE=true'
      if command -v "$bin" >/dev/null 2>&1; then "$bin" version -json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("TERRAFORM_VERSION="+str(d.get("terraform_version","unknown"))) ' || printf '%s\n' 'TERRAFORM_VERSION=UNREADABLE'
      else printf '%s\n' 'TERRAFORM_VERSION=LOCAL_BINARY_PATH'; fi
    else
      printf '%s\n' 'TERRAFORM_BINARY_AVAILABLE=false'
    fi
    if [[ -n "$root" && -d "$root" ]]; then
      count="$(find "$root" -maxdepth 1 -type f \( -name '*.tf' -o -name '*.tf.json' \) -print 2>/dev/null | wc -l | tr -d ' ')"
      printf 'TERRAFORM_ROOT_CONFIG_FILES=%s\n' "$count"
    else
      printf '%s\n' 'TERRAFORM_ROOT_CONFIG_FILES=0'
    fi
    if [[ -n "$root" && -d "$root" ]] && { command -v "$bin" >/dev/null 2>&1 || [[ -x "$bin" ]]; }; then
      printf '%s\n' 'PROVIDER_PREFLIGHT=LOCAL_PREREQUISITES_PRESENT'
      printf '%s\n' 'NOTE=This does not validate credentials, a reviewed plan, capacity, or guest boot.'
      exit 0
    fi
    printf '%s\n' 'PROVIDER_PREFLIGHT=BLOCKED'
    exit 4
    ;;
  opennebula)
    onevm="${BRAIN_OPENNEBULA_ONEVM_BIN:-onevm}"
    template_cli="${BRAIN_OPENNEBULA_ONETEMPLATE_BIN:-onetemplate}"
    template_id="${BRAIN_OPENNEBULA_TEMPLATE_ID:-}"
    onevm_ok=false; template_ok=false
    command -v "$onevm" >/dev/null 2>&1 || [[ -x "$onevm" ]] && onevm_ok=true
    command -v "$template_cli" >/dev/null 2>&1 || [[ -x "$template_cli" ]] && template_ok=true
    printf 'OPENNEBULA_ONEVM_AVAILABLE=%s\n' "$onevm_ok"
    printf 'OPENNEBULA_TEMPLATE_CLI_AVAILABLE=%s\n' "$template_ok"
    printf 'OPENNEBULA_TEMPLATE_ID_CONFIGURED=%s\n' "$([[ -n "$template_id" ]] && printf true || printf false)"
    if [[ "$onevm_ok" == true && "$template_ok" == true && -n "$template_id" ]]; then
      printf '%s\n' 'PROVIDER_PREFLIGHT=LOCAL_PREREQUISITES_PRESENT'
      printf '%s\n' 'NOTE=This does not validate OpenNebula authorization, template contents, capacity, or guest boot.'
      exit 0
    fi
    printf '%s\n' 'PROVIDER_PREFLIGHT=BLOCKED'
    exit 4
    ;;
  *)
    printf '%s\n' 'PROVIDER_STATUS=UNSUPPORTED'
    printf '%s\n' 'SUPPORTED_BACKENDS=terraform,opennebula'
    exit 4
    ;;
esac
