# CarLife-MD native runtime staging

`arm64-v8a/` contains the Android AArch64 shared library and its non-platform
runtime dependencies, built on the Realme/Termux Android environment.

The native library has been linked with Protobuf 2.5.0 using
`-Wl,--no-undefined`, and its loader test passed with this directory as the
only `LD_LIBRARY_PATH` entry. The staged runtime includes libxml2, zlib, ICU,
libiconv, and libc++ shared runtime components.

This directory is **not yet wired into an APK**. The existing
`android_executor/app` Gradle module is the Electronic Brain Executor and has
no `jniLibs`, `externalNativeBuild`, or `System.loadLibrary` integration for
CarLife-MD. Do not treat that app as the MD phone APK or install it as such.
Only add this directory to the verified phone-side MD application's
`src/main/jniLibs/arm64-v8a/` after confirming that app's source, package ID,
JNI loading entry point, and native API contract.
