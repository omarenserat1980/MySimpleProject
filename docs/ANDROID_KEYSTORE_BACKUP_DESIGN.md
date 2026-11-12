# Electronic Brain — Android Keystore Backup Design

Status: implementation draft added; device service discovery completed; APK build/runtime verification pending.

## Device evidence (Realme RMX3710, Android 15 / API 35)

- Android Keystore2 service is registered: `android.system.keystore2.IKeystoreService/default`.
- KeyMint default service is registered: `android.hardware.security.keymint.IKeyMintDevice/default`.
- Legacy Keystore service is registered.
- Termux runs as an ordinary untrusted Android app UID (not shell/system).
- OpenJDK 21 in Termux does not expose the AndroidKeyStore JCA provider: `KeyStore.getInstance("AndroidKeyStore")` returns `KeyStoreException: AndroidKeyStore not found`.
- Therefore Termux cannot safely create/use Android Keystore keys directly through its standalone JVM. Keystore operations must run inside an Android application process using Android framework APIs.
- Service registration does not prove StrongBox availability or that this device's generated AES key is hardware-backed. The app must query `KeyInfo.isInsideSecureHardware` and, on API 31+, `KeyInfo.securityLevel` after creating a key.

## Proposed ownership and trust boundary

The existing Kotlin Android Executor app (`com.electronicbrain.androidexecutor`) owns the non-exportable AES key. Termux remains responsible for preparing the archive, but never receives the key bytes.

- Alias: `electronic_brain_backup_master_v1`
- Algorithm: AES-256-GCM, 96-bit random IV, 128-bit authentication tag.
- Provider: AndroidKeyStore.
- User authentication: not required for unattended backup. This is a convenience/security trade-off; Android app sandbox and device lock remain relevant.
- The key is generated lazily on the first explicit backup action, not during diagnostics.
- The key is never exported, logged, copied to shared storage, or passed through an Intent/CLI argument.

## File format

- 8-byte magic: `EBKST01\0`
- 1-byte format version
- 1-byte IV length (must equal 12)
- IV bytes
- AES-GCM ciphertext followed by the 16-byte GCM tag

The implementation streams in 1 MiB chunks. Decryption writes only to a private `.partial` file; the destination is renamed into place only after GCM authentication succeeds. Existing destination files are never overwritten.

## Recovery warning — mandatory user disclosure

This is a device/app-installation-bound backup. Android Keystore keys are non-exportable. Uninstalling/clearing data for Electronic Brain Android Executor, deleting the alias, or resetting the phone can make the archive unrecoverable. The app must not claim portable/recovery-safe backup until a separate recovery-key wrapping flow is implemented and tested. Keep the existing Termux installation and source data until an authenticated restore test succeeds.

## Termux integration plan

1. Termux creates a plaintext archive in app-private temporary storage, not shared storage.
2. User opens the Electronic Brain Backup screen and selects the source archive using Android's Storage Access Framework (SAF).
3. The app encrypts the archive using the Android Keystore key and writes the encrypted output via SAF.
4. Restore reverses the process, authenticates GCM fully, then exposes the restored archive to the user.
5. A later integration may use a narrowly scoped explicit Activity/ContentProvider contract. Do not export a raw encrypt/decrypt service or expose filesystem paths/key material to arbitrary callers.

## Verification gates

- [ ] Build the Android Executor APK with the new Kotlin crypto class.
- [ ] Install/update only after user approval.
- [ ] Generate a key from the app process and record hardware security level (no key bytes).
- [ ] Encrypt a test file, decrypt it, compare SHA-256 hashes.
- [ ] Flip one ciphertext byte and confirm decryption fails and no final plaintext file is produced.
- [ ] Verify no overwrite and truncated-header rejection.
- [ ] Only then integrate the real Termux archive flow.
- [ ] Keep the existing passphrase-based backup tool as the recovery path until all tests pass.

## Current implementation

`android_executor/app/src/main/java/com/electronicbrain/androidexecutor/AndroidKeystoreBackup.kt` contains the AndroidKeyStore AES-GCM streaming primitive and hardware-level inspection. `MainActivity.kt` exposes the primitive through Android's Storage Access Framework (SAF). It has not yet been run inside an installed Android app. Termux-side Java probing is not a valid substitute for app-process testing.

## Follow-up implementation update — 2026-11-12

- Added `AndroidKeystoreBackup.kt` AES-256-GCM streaming implementation.
- Added SAF-based file picker and output destination flow to `MainActivity.kt`: initialize/inspect key, encrypt selected file, and authenticated decrypt/restore.
- Encryption now streams the selected source URI directly into a private encrypted `.partial` file; it does not create an extra plaintext cache copy. Decryption stages ciphertext privately and exposes plaintext only after AES-GCM authentication succeeds. Temporary files are deleted in a `finally` block. The selected destination is created by the user through Android's document picker.
- Hardware security level is displayed after the app generates its key; the earlier Termux service probe alone does not establish StrongBox or TEE backing.
- `git diff --check` passed for the changed files.
- Initial local Gradle build failed because `sdk.dir` was not configured. After setting the local Android SDK path, an offline build failed because AndroidX Media3 artifacts were not cached. An online build was stopped before completion to avoid prolonged CPU use on the phone. Kotlin compilation, APK generation, app-process Keystore access, hardware-backed key status, encryption/decryption round-trip, and tamper rejection remain unverified.
- This UI currently encrypts a user-selected file. It is not yet connected to the Termux backup archive producer. Do not treat it as the completed Electronic Brain migration backup flow.
- Do not uninstall Termux, uninstall/clear the Android Executor app, delete its Keystore alias, or delete source files until a portable recovery design and a full restore test are completed.

## Build and integration status — 2026-11-12 (continued)

- Located the existing Android SDK at `$HOME/android-sdk` (platforms android-35/android-36 and build-tools 36.0.0) and configured `android_executor/local.properties` with its local sdk.dir. This machine-local path is excluded through `.git/info/exclude`; it is not intended for source control.
- First build attempt failed because SDK location was not configured. After fixing sdk.dir, offline Gradle compilation failed because AndroidX Media3 1.11.1 artifacts were not cached.
- The local online compile on the phone was stopped before completion to avoid prolonged CPU use. This was superseded by the successful GitHub Actions build recorded below; the phone itself was not used to compile the APK.
- Updated the Activity to stream plaintext directly from the selected source URI into a private encrypted temporary file; it no longer stages an extra plaintext copy in the app cache. Decryption still stages ciphertext privately and writes the authenticated plaintext only after GCM verification succeeds.
- `git diff --check` passed after these edits. The Termux encrypted migration archive still does not exist.
- Corrected the app Gradle DSL: moved `dependencies` outside the `android` block. The local build configuration had been structurally incorrect.
- Aligned Android Gradle Plugin to 8.10.1 (Android SDK 36 support) and configured the dedicated GitHub Actions workflow to use JDK 17, Gradle 8.11.1, install Android SDK 36, compile Kotlin, run unit tests, assemble the debug APK, and upload it as an artifact.
- First GitHub Actions run (43215401987) reached the Android SDK setup step, then failed because `android-actions/setup-android@v3` attempted to install the obsolete SDK package `tools`. Kotlin compilation did not run in that attempt.
- Removed that action. The replacement exposed that `sdkmanager` is not on the default PATH in the runner; the workflow now locates it under the explicit Android SDK root. A subsequent run failed because `yes` received a broken pipe after `sdkmanager --licenses` had already exited, and the shell's `pipefail` treated that as an error. The workflow now disables `pipefail` only for the license-acceptance pipeline, while preserving failure propagation from `sdkmanager`.
- GitHub Actions run 43215842027 completed successfully: Gradle configuration, Kotlin compilation, the debug unit-test task, debug APK assembly, and artifact upload all passed.
- Downloaded and inspected the artifact locally: `app-debug.apk`, 5,861,737 bytes; package `com.electronicbrain.androidexecutor`; versionCode 2 / versionName 1.1.0; min SDK 26 / target SDK 36 / compile SDK 36. ZIP integrity and APK v2 signature verification passed. It is signed with the standard Android Debug certificate, not a production/release key. APK SHA-256: `944735d6685bd503ef2486225d16d7bc4c215c31c553cbde1474ecad64b900f2`.
- The APK has not been installed on the Realme. App-process Keystore behavior, actual hardware-backed status, encryption/decryption round-trip, and tamper rejection still require device runtime tests. The Android Keystore key is installation-bound; do not clear or uninstall the Executor app after encrypting any valuable data.

## Clean integration against current main — 2026-11-12

- Rebased the implementation work onto the current `main` snapshot in a separate clean worktree after discovering that the earlier local clone was 2,820 commits behind and its first PR contained unrelated historical changes. The broad PR was closed without merging.
- Preserved the current `PhoneIdentityKeyStore` attestation/enrollment UI in `MainActivity.kt`; the backup key uses a separate alias and SAF controls were added alongside the existing identity flow.
- Kept the Android Executor's existing service, permissions, network-security configuration, and other current-main code unchanged.
- This clean branch must run CI independently. The earlier successful CI run validated the previous branch snapshot, not this integrated current-main snapshot.
