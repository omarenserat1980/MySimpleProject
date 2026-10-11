#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="$ROOT/tools/configure_windows_real_boot_environment_secrets.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/capture"

printf '%s\n' 'https://brain-control-plane.example.invalid' > "$tmp/registry"
printf '%s\n' 'executor-token-with-at-least-32-characters' > "$tmp/token"
python3 - "$tmp/attestation" "$tmp/authority" <<'PY'
import base64, pathlib, sys
value = base64.b64encode(bytes(range(32))).decode()
for path in sys.argv[1:]:
    pathlib.Path(path).write_text(value + "\n", encoding="utf-8")
PY
printf '%s\n' 'contract-delivery-key-with-at-least-32-chars' > "$tmp/delivery"
chmod 600 "$tmp/registry" "$tmp/token" "$tmp/attestation" "$tmp/authority" "$tmp/delivery"

cat > "$tmp/bin/gh" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-} ${2:-}" in
  "auth status") exit 0 ;;
  "repo view") printf '{"nameWithOwner":"omarenserat1980/MySimpleProject"}\n' ;;
  "api repos/omarenserat1980/MySimpleProject/environments/windows-real-boot")
    printf '{"name":"windows-real-boot"}\n' ;;
  "secret list")
    if [[ "${MOCK_EXISTING:-0}" == "1" ]]; then
      printf '%s\n' BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
    fi
    ;;
  "secret set")
    name="$3"
    # Capture only a digest to prove stdin was received without retaining fixture values.
    digest="$(sha256sum | cut -d ' ' -f1)"
    printf '%s %s\n' "$name" "$digest" >> "$MOCK_CAPTURE_DIR/digests"
    ;;
  *) echo "Unexpected mocked gh call" >&2; exit 90 ;;
esac
MOCK
chmod +x "$tmp/bin/gh"

bash -n "$TOOL"
common_env=(
  "PATH=$tmp/bin:$PATH"
  "GH_REPO=omarenserat1980/MySimpleProject"
  "GITHUB_REPOSITORY=omarenserat1980/MySimpleProject"
  "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_FILE=$tmp/registry"
  "BRAIN_CLOUD_EXECUTOR_TOKEN_FILE=$tmp/token"
  "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_FILE=$tmp/attestation"
  "BRAIN_AUTHORITY_PUBLIC_KEY_B64_FILE=$tmp/authority"
  "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_FILE=$tmp/delivery"
  "MOCK_CAPTURE_DIR=$tmp/capture"
)

env "${common_env[@]}" bash "$TOOL" > "$tmp/output"
grep -Fq 'INPUT_VALIDATION=PASS' "$tmp/output"
grep -Fq 'RESULT=SETUP_REQUESTS_COMPLETE' "$tmp/output"
test "$(wc -l < "$tmp/capture/digests" | tr -d ' ')" = "5"
expected_token_digest="$(printf '%s' 'executor-token-with-at-least-32-characters' | sha256sum | cut -d ' ' -f1)"
grep -Fq "BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED $expected_token_digest" "$tmp/capture/digests"
if grep -Eq 'executor-token-with|contract-delivery-key-with|https://brain-control-plane.example.invalid' "$tmp/output"; then
  echo "FAIL: output disclosed a fixture value" >&2
  exit 1
fi

# Existing secret names are preserved unless explicit overwrite authorization is supplied.
: > "$tmp/capture/digests"
env "${common_env[@]}" MOCK_EXISTING=1 bash "$TOOL" > "$tmp/preserved"
grep -Fq 'SECRET_ACTION=BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED:PRESERVED_ALREADY_EXISTS' "$tmp/preserved"
test ! -s "$tmp/capture/digests"

# Missing input must fail before any secret mutation.
set +e
env "${common_env[@]}" BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_FILE="$tmp/no-such-file" bash "$TOOL" > "$tmp/missing" 2>&1
code=$?
set -e
test "$code" -eq 2
grep -Fq 'RESULT=BLOCKED_INPUT_FILE_REQUIRED:BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED' "$tmp/missing"
test ! -s "$tmp/capture/digests"

echo 'RESULT=PASS'
echo 'CASES=bash-syntax,all-inputs-prevalidated,stdin-secret-delivery,no-value-disclosure,preserve-existing,fail-closed'
