#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${BRAIN_ROOT:-$HOME/MySimpleProject}"
AGENT_DIR="$HOME/.brain-agent"
BOOT_DIR="$HOME/.termux/boot"
ENV_FILE="$AGENT_DIR/agent.env"
mkdir -p "$AGENT_DIR" "$BOOT_DIR"
cat > "$AGENT_DIR/start-agent.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${BRAIN_ROOT:-$HOME/MySimpleProject}"
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock || true
cd "$ROOT"
set -a
[ -f "$HOME/.brain-agent/agent.env" ] && . "$HOME/.brain-agent/agent.env"
set +a
exec python "$ROOT/brain_emulator_agent/brain_device_agent_v2.py"
EOF
chmod +x "$AGENT_DIR/start-agent.sh"
cat > "$BOOT_DIR/start-brain-agent" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 5
exec "$HOME/.brain-agent/start-agent.sh"
EOF
chmod +x "$BOOT_DIR/start-brain-agent"
if [ ! -f "$ENV_FILE" ]; then
cat > "$ENV_FILE" <<EOF
BRAIN_ROOT=$ROOT
BRAIN_URL=http://127.0.0.1:8012
V12_AGENT_ID=redmi3-01
V12_POLL_SECONDS=5
V12_AGENT_KEY_FILE=$AGENT_DIR/agent.key
EOF
chmod 600 "$ENV_FILE"
fi
echo "Brain Termux Agent installed."
echo "Edit $ENV_FILE and create $AGENT_DIR/agent.key before start."
