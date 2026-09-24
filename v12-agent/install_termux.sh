#!/data/data/com.termux/files/usr/bin/bash
set -e
mkdir -p "$HOME/v12-agent"
cd "$HOME/v12-agent"
pkg install -y python curl >/dev/null
curl -fsSL "https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main/v12-agent/agent.py" -o agent.py
curl -fsSL "https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main/v12-agent/start.sh" -o start.sh
chmod 700 start.sh agent.py
if [ ! -s "$HOME/v12-agent/agent.key" ]; then
  echo "AGENT_KEY_MISSING"
  echo "Create the key first and save it to $HOME/v12-agent/agent.key"
  exit 2
fi
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/start-v12-agent" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
exec "$HOME/v12-agent/start.sh"
BOOT
chmod 700 "$HOME/.termux/boot/start-v12-agent"
"$HOME/v12-agent/start.sh"
echo "V12_TERMUX_AUTOSTART_READY"
