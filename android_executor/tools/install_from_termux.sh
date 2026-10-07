#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
APK="${1:-$HOME/storage/downloads/electronic-brain-android-executor-debug (5) (2)/app-debug.apk}"
PACKAGE="com.electronicbrain.androidexecutor"
echo "[BRAIN] Android Executor installer"
echo "[BRAIN] APK: $APK"
if [ ! -f "$APK" ]; then echo "[ERROR] APK not found"; exit 2; fi
echo "[CHECK] APK bytes: $(wc -c < "$APK")"
if command -v termux-open >/dev/null 2>&1; then
  echo "[ACTION] Opening Android package installer..."
  termux-open "$APK" || true
else
  echo "[ERROR] termux-open is unavailable"; exit 3
fi
echo "[VERIFY] Waiting for Android package installation..."
for i in $(seq 1 30); do
  if cmd package path "$PACKAGE" >/dev/null 2>&1; then
    echo "[OK] $PACKAGE installed"
    cmd package path "$PACKAGE"
    exit 0
  fi
  sleep 2
done
echo "[PENDING] Android installer did not finish within 60s."
echo "[NEXT] Complete the Android install dialog, then rerun: cmd package path $PACKAGE"
exit 10
