#!/usr/bin/env bash
set -euo pipefail

SERVICE="brain6-168h.service"
UNIT_DIR="$HOME/.config/systemd/user"

# Retire the old service if present; do not start a replacement implicitly.
systemctl --user disable --now "$SERVICE" >/dev/null 2>&1 || true
rm -f "$UNIT_DIR/$SERVICE"
systemctl --user daemon-reload
systemctl --user reset-failed "$SERVICE" >/dev/null 2>&1 || true

echo "BRAIN6_RETIRED: legacy service disabled and removed from the user systemd unit directory."
echo "No Brain runtime or workload was started."
echo "Canonical Brain core entrypoint: python3 -m brain_v12.app"
