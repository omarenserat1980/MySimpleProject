#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="$ROOT/tools/describe_executor_token_secret.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
cat > "$tmp/bin/gh" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-} ${2:-}" in
  "auth status") exit 0 ;;
  "repo view") printf '{"nameWithOwner":"omarenserat1980/MySimpleProject"}\n' ;;
  "secret list")
    if [[ "${MOCK_SECRET_PRESENT:-0}" == 1 ]]; then
      printf '%s\n' BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
    fi
    ;;
  "api repos/omarenserat1980/MySimpleProject/contents/brain_v12/brain/cloud_executor_attestation_api.py?ref=main")
    printf '%s' 'IyBCRUFyIENsb3VkIEV4ZWN1dG9yIEVub2xsbWVudHMgQlJBSU5fQ0xPVURfRVhFQ1VUT1JfRU5ST0xMTUVOVFNfU0hBMjU2X0pTT04K' ;;
  "api repos/omarenserat1980/MySimpleProject/contents/brain_v12/CLOUD_EXECUTOR_CONTROL_PLANE_SETUP.md?ref=main")
    printf '%s' 'QlJBSU5fQ0xPVURfRVhFQ1VUT1JfRU5ST0xMTUVOVFNfU0hBMjU2X0pTT04K' ;;
  *) echo "Unexpected mocked gh call" >&2; exit 90 ;;
esac
MOCK
chmod +x "$tmp/bin/gh"
bash -n "$TOOL"
for state in 0 1; do
  output="$(PATH="$tmp/bin:$PATH" MOCK_SECRET_PRESENT="$state" GH_REPO=omarenserat1980/MySimpleProject bash "$TOOL")"
  grep -Fq 'SECRET_VALUES=NEVER_READ_OR_PRINTED' <<< "$output"
  grep -Fq 'REMOTE_SOURCE_REFERENCE=FOUND' <<< "$output"
  if [[ "$state" == 0 ]]; then
    grep -Fq 'GITHUB_SECRET_NAME=MISSING' <<< "$output"
    grep -Fq 'SECRET_NAME_STATUS=BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED:MISSING' <<< "$output"
  else
    grep -Fq 'GITHUB_SECRET_NAME=PRESENT' <<< "$output"
    grep -Fq 'SECRET_NAME_STATUS=BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED:PRESENT' <<< "$output"
  fi
done
echo 'RESULT=PASS'
echo 'CASES=syntax,secret-missing,secret-present,remote-source-reference,secret-values-not-printed'
