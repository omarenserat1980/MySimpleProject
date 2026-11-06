#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/app/src/main/assets/carlife-native/arm64-v8a"
DEST="$ROOT/app/src/main/jniLibs/arm64-v8a"
mkdir -p "$DEST"
rm -f "$DEST"/*.so "$DEST"/*.so.*

# Give bundled ICU/XML/zlib libraries app-private names to prevent Android's
# linker namespace from binding generic libicuuc.so to the platform ICU.
cp "$SRC/libc++_shared.so" "$DEST/libc++_shared.so"
cp "$SRC/libcarlifevehicle.so" "$DEST/libcarlifevehicle.so"
cp "$SRC/libiconv.so" "$DEST/libiconv.so"
cp "$SRC/libicudata.so.78" "$DEST/libbicudata.so"
cp "$SRC/libicuuc.so.78" "$DEST/libbicuuc.so"
cp "$SRC/libxml2.so.16" "$DEST/libbxml2.so"
cp "$SRC/libz.so.1" "$DEST/libbz.so"

python3 - "$DEST" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
renames = {
    b"libicudata.so.78": b"libbicudata.so",
    b"libicuuc.so.78": b"libbicuuc.so",
    b"libxml2.so.16": b"libbxml2.so",
    b"libz.so.1": b"libbz.so",
}
for path in sorted(root.glob("*.so")):
    data = path.read_bytes()
    original = data
    for old, new in renames.items():
        if len(new) > len(old):
            raise SystemExit(f"Unsafe growing rename: {old!r}")
        data = data.replace(old + b"\0", new + b"\0" * (len(old) - len(new) + 1))
    if data != original:
        path.write_bytes(data)
PY

for f in "$DEST"/*.so; do
  readelf -h "$f" >/dev/null
  readelf -d "$f" | grep -q 'GNU_HASH\|HASH' || { echo "Missing ELF hash table: $f" >&2; exit 1; }
done

for pair in \
  "libcarlifevehicle.so:libbz.so" \
  "libcarlifevehicle.so:libbxml2.so" \
  "libbxml2.so:libbz.so" \
  "libbxml2.so:libbicuuc.so" \
  "libbicuuc.so:libbicudata.so"; do
  parent="${pair%%:*}"; dependency="${pair#*:}"
  readelf -d "$DEST/$parent" | grep -F "[$dependency]" >/dev/null || {
    echo "$parent does not request $dependency" >&2; exit 1;
  }
  test -s "$DEST/$dependency" || { echo "Missing dependency $dependency" >&2; exit 1; }
done

# Ensure libxml2's ICU callback is exported by the bundled ICU library.
nm -D --defined-only "$DEST/libbicuuc.so" | grep -F 'UCNV_TO_U_CALLBACK_STOP_78'
nm -D --undefined-only "$DEST/libbxml2.so" | grep -F 'UCNV_TO_U_CALLBACK_STOP_78'

echo 'Prepared app-private CarLife native dependency closure.'
for f in "$DEST"/*.so; do
  echo "### $(basename "$f")"
  readelf -d "$f" | grep -E 'NEEDED|SONAME' || true
done
