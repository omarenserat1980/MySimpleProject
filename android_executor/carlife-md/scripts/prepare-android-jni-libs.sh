#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/app/src/main/assets/carlife-native/arm64-v8a"
DEST="$ROOT/app/src/main/jniLibs/arm64-v8a"
mkdir -p "$DEST"
# Remove stale unversioned aliases from earlier packaging experiments.
rm -f "$DEST/libicudata.so" "$DEST/libicuuc.so" "$DEST/libxml2.so" "$DEST/libz.so"

# Preserve the vendor ELF images byte-for-byte. In particular, do not run
# patchelf on libcarlifevehicle.so: its original PT_LOAD layout and GNU hash
# table are required by Android's linker.
cp "$SRC/libc++_shared.so" "$DEST/libc++_shared.so"
cp "$SRC/libcarlifevehicle.so" "$DEST/libcarlifevehicle.so"
cp "$SRC/libiconv.so" "$DEST/libiconv.so"
cp "$SRC/libicudata.so.78" "$DEST/libicudata.so.78"
cp "$SRC/libicuuc.so.78" "$DEST/libicuuc.so.78"
cp "$SRC/libxml2.so.16" "$DEST/libxml2.so.16"
cp "$SRC/libz.so.1" "$DEST/libz.so.1"

for f in "$DEST"/*.so "$DEST"/*.so.*; do
  readelf -h "$f" >/dev/null
  readelf -d "$f" | grep -q 'GNU_HASH\|HASH' || { echo "Missing ELF hash table: $f" >&2; exit 1; }
done
cmp -s "$SRC/libcarlifevehicle.so" "$DEST/libcarlifevehicle.so"
echo 'Prepared Android native libraries without rewriting vendor ELF files.'
find "$DEST" -maxdepth 1 -type f -printf '%f\n' | sort
