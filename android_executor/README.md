# Electronic Brain — PHONE-ONLY Android Executor

Native Android executor for Electronic Brain.

## Runtime bootstrap

The executor now:
- checks Brain `/health`;
- invokes the Termux runtime bootstrap when Brain is unavailable;
- exposes the gated `brain_runtime_launch` task;
- reports bootstrap evidence back through the normal executor result path.

## CI verification

The Android Executor Build workflow is an authoritative build gate. It must produce a fresh `app-debug.apk` artifact from the current commit before this executor can be considered installable.

Pre-fix APK artifacts must not be reused for runtime verification.

CI retrigger marker: 1791439970012
