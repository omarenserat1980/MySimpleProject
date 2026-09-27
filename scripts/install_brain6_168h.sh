#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
sed "s#%h/MySimpleProject#$ROOT#g" "$ROOT/deploy/brain6-168h.service" > "$UNIT_DIR/brain6-168h.service"
systemctl --user daemon-reload
systemctl --user enable --now brain6-168h.service
echo "Brain 6 168H service started."
echo "Status: systemctl --user status brain6-168h.service"
echo "Live logs: journalctl --user -u brain6-168h.service -f"
