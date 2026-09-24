#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$HOME/v12-agent"
if [ ! -s "$HOME/v12-agent/agent.key" ]; then
  echo "V12_AGENT_KEY_MISSING"
  exit 1
fi
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock || true
pkill -f "$HOME/v12-agent/agent.py" 2>/dev/null || true
nohup python "$HOME/v12-agent/agent.py" >> "$HOME/v12-agent/agent.log" 2>&1 &
echo $! > "$HOME/v12-agent/agent.pid"
echo "V12_TERMUX_AGENT_STARTED"
