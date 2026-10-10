#!/usr/bin/env bash
# Electronic Brain one-line bootstrap for Termux, Linux, and macOS.
# Safe by default: never resets a repository, overwrites an existing command,
# prints secrets, or fabricates an agent identity/key mapping.
set -Eeuo pipefail

REPO_URL="https://github.com/omarenserat1980/MySimpleProject.git"
RAW_BASE="https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main"
if [[ -n "${BRAIN_ONE_SOURCE_URL:-}" ]]; then RAW_BASE="${BRAIN_ONE_SOURCE_URL%/brain-one.sh}"; fi
ACTION="${1:-activate}"
HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then echo "BRAIN_ERROR=HOME_NOT_SET" >&2; exit 2; fi
say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
is_termux() { [[ "${PREFIX:-}" == *com.termux/files/usr ]]; }

INSTALL_DIR="$HOME_DIR/.local/share/brain"
mkdir -p "$INSTALL_DIR"

# Never run a dirty or non-main checkout as the activation source. Preserve it,
# and use a dedicated managed runtime checkout instead.
if [[ -n "${BRAIN_ROOT:-}" && -d "${BRAIN_ROOT}/.git" ]]; then
  CANDIDATE="$BRAIN_ROOT"
elif [[ -d "$HOME_DIR/MySimpleProject/.git" ]]; then
  CANDIDATE="$HOME_DIR/MySimpleProject"
else
  CANDIDATE=""
fi

if [[ -n "$CANDIDATE" ]]; then
  CANDIDATE_BRANCH="$(git -C "$CANDIDATE" branch --show-current 2>/dev/null || true)"
  CANDIDATE_DIRTY="$(git -C "$CANDIDATE" status --porcelain 2>/dev/null || true)"
else
  CANDIDATE_BRANCH=""
  CANDIDATE_DIRTY=""
fi

if [[ -n "$CANDIDATE" && "$CANDIDATE_BRANCH" == "main" && -z "$CANDIDATE_DIRTY" ]]; then
  ROOT="$CANDIDATE"
  # Fast-forward only a clean main checkout; never reset or discard local work.
  if have git; then
    git -C "$ROOT" fetch --quiet origin main
    git -C "$ROOT" merge --ff-only --quiet origin/main
  fi
else
  RUNTIME_DIR="$INSTALL_DIR/runtime"
  ROOT="$RUNTIME_DIR/MySimpleProject"
  mkdir -p "$RUNTIME_DIR"
  if [[ ! -e "$ROOT" ]]; then
    have git || { say "BRAIN_ERROR=GIT_REQUIRED_FOR_RUNTIME_INSTALL"; exit 20; }
    git clone --depth 1 --branch main "$REPO_URL" "$ROOT"
  else
    if [[ ! -d "$ROOT/.git" ]]; then
      say "BRAIN_ERROR=RUNTIME_PATH_EXISTS_NOT_GIT"
      say "Nothing was overwritten: $ROOT"
      exit 21
    fi
    RUNTIME_BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
    RUNTIME_DIRTY="$(git -C "$ROOT" status --porcelain 2>/dev/null || true)"
    if [[ "$RUNTIME_BRANCH" != "main" || -n "$RUNTIME_DIRTY" ]]; then
      say "BRAIN_ERROR=MANAGED_RUNTIME_NOT_CLEAN_MAIN"
      say "Preserve and inspect: $ROOT"
      exit 22
    fi
    git -C "$ROOT" fetch --quiet origin main
    git -C "$ROOT" merge --ff-only --quiet origin/main
  fi
  say "BRAIN_NOTE=existing_checkout_preserved"
fi

[[ -f "$ROOT/brain_v12/tools/brain_runtime_bootstrap.sh" ]] || {
  say "BRAIN_ERROR=RUNTIME_FILES_MISSING"
  say "Repository was not reset or cleaned. Review the checkout before retrying."
  exit 22
}

INSTALL_DIR="$HOME_DIR/.local/share/brain"
mkdir -p "$INSTALL_DIR"
SELF_PATH="$INSTALL_DIR/brain-one.sh"
SOURCE_FILE="${BASH_SOURCE[0]:-}"
if [[ "$SOURCE_FILE" != "$SELF_PATH" ]]; then
  if [[ -f "$SELF_PATH" ]] && ! grep -q 'Electronic Brain one-line bootstrap' "$SELF_PATH" 2>/dev/null; then
    say "BRAIN_ERROR=INSTALL_TARGET_EXISTS_UNOWNED"
    say "Nothing was overwritten: $SELF_PATH"
    exit 23
  fi
  if [[ -f "$SOURCE_FILE" ]]; then
    cp "$SOURCE_FILE" "$SELF_PATH"
  else
    # Supports the one-line curl | bash invocation where source is a pipe.
    have curl || { say "BRAIN_ERROR=CURL_REQUIRED_TO_INSTALL_COMMAND"; exit 24; }
    tmp="$SELF_PATH.tmp.$$"
    curl -fsSL "$RAW_BASE/brain-one.sh" -o "$tmp"
    grep -q 'Electronic Brain one-line bootstrap' "$tmp" || { rm -f "$tmp"; say "BRAIN_ERROR=DOWNLOADED_SCRIPT_UNVERIFIED"; exit 24; }
    chmod 700 "$tmp"
    mv -f "$tmp" "$SELF_PATH"
  fi
  chmod 700 "$SELF_PATH"
fi

install_command() {
  local bin_dir target tmp
  if is_termux; then bin_dir="$PREFIX/bin"
  elif [[ "${OSTYPE:-}" == darwin* || "${OSTYPE:-}" == linux* ]]; then bin_dir="$HOME_DIR/.local/bin"
  else say "BRAIN_ERROR=UNSUPPORTED_SHELL_PLATFORM"; exit 25; fi
  mkdir -p "$bin_dir"
  target="$bin_dir/brain"
  if [[ -e "$target" || -L "$target" ]]; then
    if grep -q 'Electronic Brain command shim' "$target" 2>/dev/null; then
      say "BRAIN_INSTALL already_installed=true"; return 0
    fi
    say "BRAIN_ERROR=COMMAND_NAME_ALREADY_IN_USE"
    say "Nothing was overwritten: $target"; exit 26
  fi
  tmp="$target.tmp.$$"
  {
    printf '#!/usr/bin/env bash\n'
    printf '# Electronic Brain command shim\n'
    printf 'export BRAIN_ROOT=%q\n' "$ROOT"
    printf 'exec bash %q "\$@"\n' "$SELF_PATH"
  } > "$tmp"
  chmod 700 "$tmp"; mv "$tmp" "$target"
  case ":$PATH:" in *":$bin_dir:"*) ;; *) say "BRAIN_NOTE=add $bin_dir to PATH";; esac
  say "BRAIN_INSTALL installed=true"
}

status() {
  say "BRAIN_ONE_LINE_STATUS"
  say "platform=$(uname -s 2>/dev/null || echo unknown)"
  say "architecture=$(uname -m 2>/dev/null || echo unknown)"
  say "repository=$ROOT"
  say "agent_config=$([[ -f "$HOME_DIR/v12-agent/agent_config.sh" ]] && echo present || echo absent)"
  say "agent_key_file=$([[ -s "$HOME_DIR/v12-agent/agent.key" ]] && echo present || echo absent)"
  say "control_key_file=$([[ -f "$HOME_DIR/.brain_env" ]] && echo env_file_present_not_read || echo absent)"
  say "git_commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  say "worktree=$([[ -z "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]] && echo clean || echo has_changes)"
  if have curl; then
    local url code
    url="${V12_BRAIN_URL:-http://127.0.0.1:8012}"
    code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 4 "${url%/}/health" 2>/dev/null || true)"
    say "api_health=HTTP_${code:-NO_RESPONSE}"
  else say "api_health=NOT_CHECKED_CURL_MISSING"; fi
}

case "$ACTION" in
  install) install_command; status ;;
  status|diagnose) status ;;
  activate|up|start)
    install_command
    say "BRAIN_ACTIVATE starting_runtime=true"
    bash "$ROOT/brain_v12/tools/brain_runtime_bootstrap.sh"
    sleep 2
    status
    ;;
  help|-h|--help)
    say "Electronic Brain one-line control: install | activate | status"
    say "Supported shell platforms: Termux, Linux, macOS. Windows uses the PowerShell companion with WSL."
    ;;
  *) say "BRAIN_ERROR=UNKNOWN_ACTION action=$ACTION"; exit 2 ;;
esac
