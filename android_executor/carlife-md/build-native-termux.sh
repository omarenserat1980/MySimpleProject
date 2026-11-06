#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_ROOT="$PKG_DIR/upstream/LibSource"
PB_PREFIX="$HOME/.cache/carlife-protobuf-2.5.0/install"
STAGE="$PKG_DIR/native/arm64-v8a"

if [[ -z "${PREFIX:-}" || ! -d "$PREFIX/lib" ]]; then
  echo "ERROR: run this script inside Termux (PREFIX/lib not found)." >&2
  exit 2
fi
if [[ ! -f "$PB_PREFIX/lib/libprotobuf.a" ]]; then
  echo "ERROR: isolated Protobuf 2.5.0 build is missing: $PB_PREFIX" >&2
  exit 2
fi

CFLAGS="-g -Wall -W -fPIC -DGOOGLE_PROTOBUF_NO_THREAD_SAFETY -I $LIB_ROOT/protobuf/cc/include -I $LIB_ROOT/include -I $PB_PREFIX/include -I $PB_PREFIX/include/google/protobuf/io -I /usr/include -I /usr/include/libxml2"
LFLAGS="-L$PB_PREFIX/lib -lprotobuf -lz -lxml2"

cd "$LIB_ROOT"
make -f Makefile.linux -j1 carlifelib CFLAGS="$CFLAGS" LFLAGS="$LFLAGS"
# The upstream Makefile omits LFLAGS from its shared-library link command.
# Relink strictly so unresolved symbols fail the build.
g++ -shared -Wl,--no-undefined -o libcarlifevehicle.so built-in.o $LFLAGS
mkdir -p obj "$STAGE"
cp libcarlifevehicle.so obj/libcarlifevehicle.so
cp libcarlifevehicle.so "$STAGE/libcarlifevehicle.so"

# Package the complete non-platform runtime dependency closure for arm64-v8a.
for name in libxml2.so.16 libz.so.1 libicuuc.so.78 libicudata.so.78 libiconv.so libc++_shared.so; do
  test -e "$PREFIX/lib/$name" || { echo "ERROR: missing runtime dependency $name" >&2; exit 3; }
  cp -L "$PREFIX/lib/$name" "$STAGE/$name"
done

file "$STAGE/libcarlifevehicle.so"
readelf -h "$STAGE/libcarlifevehicle.so" | grep -E 'Class:|Machine:'
echo "Native arm64-v8a staging complete: $STAGE"
echo "This is not an APK build; integrate only into the verified phone-side MD app."
