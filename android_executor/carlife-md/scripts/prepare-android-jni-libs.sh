#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/app/src/main/assets/carlife-native/arm64-v8a"
DEST="$ROOT/app/src/main/jniLibs/arm64-v8a"
mkdir -p "$DEST"
rm -f "$DEST"/*.so "$DEST"/*.so.*

# Android's jniLibs packaging only installs conventional *.so filenames.
# Copy vendor files, then rename versioned DT_NEEDED/DT_SONAME strings in-place.
# The replacements are shorter and zero-padded to the original string length:
# ELF offsets, program headers, PT_LOAD layout and hash tables remain untouched.
cp "$SRC/libc++_shared.so" "$DEST/libc++_shared.so"
cp "$SRC/libcarlifevehicle.so" "$DEST/libcarlifevehicle.so"
cp "$SRC/libiconv.so" "$DEST/libiconv.so"
cp "$SRC/libicudata.so.78" "$DEST/libicudata.so"
cp "$SRC/libicuuc.so.78" "$DEST/libicuuc.so"
cp "$SRC/libxml2.so.16" "$DEST/libxml2.so"
cp "$SRC/libz.so.1" "$DEST/libz.so"

python3 - "$DEST" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
renames = {
    b"libicudata.so.78": b"libicudata.so",
    b"libicuuc.so.78": b"libicuuc.so",
    b"libxml2.so.16": b"libxml2.so",
    b"libz.so.1": b"libz.so",
}
for path in sorted(root.glob("*.so")):
    data = path.read_bytes()
    original = data
    for old, new in renames.items():
        if len(new) > len(old):
            raise SystemExit(f"Unsafe growing rename: {old!r}")
        # Dynamic string table entries are NUL-terminated. Preserve each
        # entry's exact byte width so no ELF offsets or hash data move.
        data = data.replace(old + b"\0", new + b"\0" * (len(old) - len(new) + 1))
    if data != original:
        path.write_bytes(data)
PY

for f in "$DEST"/*.so; do
  readelf -h "$f" >/dev/null
  readelf -d "$f" | grep -q 'GNU_HASH\|HASH' || { echo "Missing ELF hash table: $f" >&2; exit 1; }
done

# Assert every private dependency resolves to a packaged conventional .so.
for pair in \
  "libcarlifevehicle.so:libz.so" \
  "libcarlifevehicle.so:libxml2.so" \
  "libxml2.so:libz.so" \
  "libxml2.so:libicuuc.so" \
  "libicuuc.so:libicudata.so"; do
  parent="${pair%%:*}"; dependency="${pair#*:}"
  readelf -d "$DEST/$parent" | grep -F "[$dependency]" >/dev/null || {
    echo "$parent does not request $dependency" >&2; exit 1;
  }
  test -s "$DEST/$dependency" || { echo "Missing dependency $dependency" >&2; exit 1; }
done

echo 'Prepared Android-compatible .so dependency closure with in-place ELF string renames.'
for f in "$DEST"/*.so; do
  echo "### $(basename "$f")"
  readelf -d "$f" | grep -E 'NEEDED|SONAME' || true
done
