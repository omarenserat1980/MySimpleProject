#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SRC="$ROOT/app/src/main/assets/carlife-native/arm64-v8a"
DEST="$ROOT/app/src/main/jniLibs/arm64-v8a"
command -v patchelf >/dev/null || { echo 'patchelf is required' >&2; exit 2; }
mkdir -p "$DEST"
cp "$SRC/libc++_shared.so" "$DEST/libc++_shared.so"
cp "$SRC/libcarlifevehicle.so" "$DEST/libcarlifevehicle.so"
cp "$SRC/libiconv.so" "$DEST/libiconv.so"
cp "$SRC/libicudata.so.78" "$DEST/libicudata.so"
cp "$SRC/libicuuc.so.78" "$DEST/libicuuc.so"
cp "$SRC/libxml2.so.16" "$DEST/libxml2.so"
cp "$SRC/libz.so.1" "$DEST/libz.so"

# Android's nativeLibraryDir reliably packages unversioned *.so names.
# Normalize DT_NEEDED names to those packaged filenames.
patchelf --replace-needed libz.so.1 libz.so "$DEST/libcarlifevehicle.so"
patchelf --replace-needed libxml2.so.16 libxml2.so "$DEST/libcarlifevehicle.so"
patchelf --replace-needed libz.so.1 libz.so "$DEST/libxml2.so"
patchelf --replace-needed libicuuc.so.78 libicuuc.so "$DEST/libxml2.so"
patchelf --replace-needed libicudata.so.78 libicudata.so "$DEST/libicuuc.so"

for f in "$DEST"/*.so; do
  readelf -h "$f" >/dev/null
done

echo 'Prepared Android native library directory:'
find "$DEST" -maxdepth 1 -type f -printf '%f\n' | sort
echo 'Remaining non-system DT_NEEDED entries:'
for f in "$DEST"/*.so; do
  echo "[$(basename "$f")]"
  readelf -d "$f" | grep NEEDED || true
done
