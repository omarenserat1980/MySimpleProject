#!/usr/bin/env bash
# Electronic Brain one-line bootstrap for Termux, Linux, and macOS.
# Safe by default: never resets a repository, overwrites an existing command,
# prints secrets, or fabricates an agent identity/key mapping.
set -Eeuo pipefail

REPO_URL="https://github.com/omarenserat1980/MySimpleProject.git"
RAW_BASE="https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main"
ACTION="${1:-activate}"
HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then echo "BRAIN_ERROR=HOME_NOT_SET" >&2; exit 2; fi
say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
is_termux() { [[ "${PREFIX:-}" == *com.termux/files/usr ]]; }

if [[ -n "${BRAIN_ROOT:-}" && -d "${BRAIN_ROOT}/.git" ]]; then
  ROOT="$BRAIN_ROOT"
elif [[ -d "$HOME_DIR/MySimpleProject/.git" ]]; then
  ROOT="$HOME_DIR/MySimpleProject"
elif [[ ! -e "$HOME_DIR/MySimpleProject" ]]; then
  if ! have git; then say "BRAIN_ERROR=GIT_REQUIRED_FOR_FIRST_INSTALL"; exit 20; fi
  git clone --depth 1 --branch main "$REPO_URL" "$HOME_DIR/MySimpleProject"
  ROOT="$HOME_DIR/MySimpleProject"
else
  say "BRAIN_ERROR=EXISTING_PATH_IS_NOT_A_GIT_REPOSITORY"
  say "Nothing was overwritten. Set BRAIN_ROOT to a valid checkout and retry."
  exit 21
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
