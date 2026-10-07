#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/MySimpleProject"
HABITAT="$ROOT/brain_android_habitat/termux_boot.sh"
BOOT="$HOME/.termux/boot"
TARGET="$BOOT/00-brain-runtime"

if [ ! -f "$HABITAT" ]; then
  echo "BRAIN_HABITAT_ERROR: termux_boot.sh not found: $HABITAT" >&2
  exit 20
fi

mkdir -p "$BOOT"
if [ -f "$TARGET" ]; then
  cp "$TARGET" "$TARGET.pre_habitat.$(date +%Y%m%d%H%M%S).bak"
fi

cat > "$TARGET" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
termux-wake-lock || true
exec "$HOME/MySimpleProject/brain_android_habitat/termux_boot.sh"
EOF
chmod 700 "$TARGET"

echo "BRAIN_HABITAT_BOOT_REPAIRED target=$TARGET"
echo "BRAIN_HABITAT_NEXT=restart Termux:Boot or run: $TARGET"
