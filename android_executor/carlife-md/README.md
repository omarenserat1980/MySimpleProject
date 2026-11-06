# CarLife MD CTRL receive integration

This integration package targets the **phone-side MD branch** only:
`brain/honda-android-network-sqlite` in `omarenserat1980/MySimpleProject`.

It pins `Doris-duo/CarLife-MD-Lib` at commit
`b3cc871f7c5c4b41947a3c512caee76624eaffd9` and applies the CTRL receive patch
to the upstream source as a submodule working-tree change.

## Why this is staged, not a completed APK integration

The MD repository did not contain `CConnectManager` or
`CTranRecvPackageProcess`. The correct source therefore has to be introduced
as a separately licensed upstream component. The upstream repository includes
an Apache-2.0 LICENSE. This package does not copy its source into the MD app.

The patch adds `readCtrlData`, reads the CTRL frame header and payload, marks
the CTRL socket disconnected on read failure, and rejects payloads larger
than `CTRL_DATA_SIZE`. The source allocates `CTRL_DATA_SIZE` bytes for the
CTRL receive buffer; upstream defines it as 10 KiB.

## Apply

1. Clone `omarenserat1980/MySimpleProject`.
2. Check out `brain/honda-android-network-sqlite`.
3. Ensure the working tree is clean.
4. Copy this `carlife-md-ctrl-integration` directory to
   `android_executor/carlife-md` in the clone.
5. Run:
   `bash android_executor/carlife-md/apply-on-md-branch.sh`

The script refuses to run on another branch, refuses a dirty working tree,
pins the exact upstream commit, and runs `git apply --check` before applying.

## Required validation after applying

- Inspect the resulting diff and verify no unrelated files changed.
- Compile the native library with the supported Android NDK/toolchain.
- Add/run CTRL receive tests: null socket, read failure/disconnect, valid
  header+payload, zero-length payload, oversized payload, fragmented TCP
  delivery, and CTRL message dispatch.
- Run ASan/UBSan where supported.
- Integrate the native library into the **phone MD APK** build only.
- Confirm actual transport role and authorized Baidu/Honda authentication
  before any in-car test.

This package does not claim that the native library compiles, that the MD APK
builds, or that a Honda unit interoperates. It does not contain credentials,
keys, or production secrets.

## Native build result (Realme RMX3710 / Termux)

The pinned upstream library was compiled for Android `arm64-v8a` using the
isolated Protobuf 2.5.0 build under `$HOME/.cache/carlife-protobuf-2.5.0`.
The shared object was relinked with `-Wl,--no-undefined`; the CTRL receive
symbols were verified and a `dlopen` smoke test passed with the staged runtime
folder as the library search path. Runtime dependencies are staged under
`native/arm64-v8a/` (about 44 MiB total).

Rebuild with `bash android_executor/carlife-md/build-native-termux.sh` from the
MD branch on Termux. The script does not build an APK. The existing
`android_executor/app` module is not yet proven to be the CarLife-MD phone app
and currently has no native library loading configuration. APK integration
and CTRL protocol tests remain pending.

## Android APK packaging update

The phone app now stores all ARM64 native dependencies under `app/src/main/assets/carlife-native/arm64-v8a/` because Android Gradle Plugin only packages standard `.so` names from `jniLibs`; upstream runtime dependencies use versioned SONAMEs such as `libxml2.so.16`. `CarLifeNativeLoader` extracts and loads dependencies in SONAME order. `CarLifeMdActivity` exposes USB descriptor discovery. The APK build does not yet implement JNI calls into the C++ API, CarLife authentication/session setup, or media streaming.

## Android JNI bridge (MD)

The phone app now builds `libbraincarlife_jni.so` with the Android NDK and links it to the pinned ARM64 `libcarlifevehicle.so`. `CarLifeJni.nativeInitialize()` only initializes the library singleton; it does not open sockets or start a CarLife session. The explicit `nativeConnectionSetup(mdIp, interfaceName)` entry point validates an IPv4 address and interface-name length, and is deliberately not called by the diagnostics screen until the actual MD network route/interface is established. The no-argument upstream `connectionSetup()` is intentionally not exposed because it invokes `adb forward` commands. Authentication, callbacks, channel receive loops, USB bulk transport, and media streaming remain separate unfinished integration work.


### Android linker namespace packaging fix

The phone's `System.load()` of files extracted into `filesDir` did not make those dependencies discoverable to the classloader linker namespace when loading `libbraincarlife_jni.so` from the APK. The Android build now normalizes the pinned runtime's versioned ELF dependencies to unversioned `.so` filenames using `patchelf`, places the complete dependency closure in `app/src/main/jniLibs/arm64-v8a`, and loads the JNI bridge from Android's `nativeLibraryDir` with `System.loadLibrary`. The preparation script is `scripts/prepare-android-jni-libs.sh`; CI runs it before Gradle. This addresses library discovery only; it does not establish a CarLife session.
