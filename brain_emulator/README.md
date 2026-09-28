# BRAIN Termux Emulator

BRAIN Termux Emulator is the native Android command/runtime layer for Electronic Brain.

It replaces the old dependency on the Termux application for Brain operations. The Android app owns the terminal UI and BRAIN home, while BRAIN Cloud Hub owns long-running services, Docker lifecycle, cinematic jobs, FFmpeg/QC, and factory APIs.

## Architecture

Android BRAIN Termux Emulator
-> localhost:8787
-> BRAIN Cloud Hub
-> Brain services / Cinematic Factory / Image Factory / QC

## Rules

- No Termux installation is required.
- No `pkg`, `.termux/boot`, or Termux-only shebang is required.
- Long-running production belongs to BRAIN Cloud Hub.
- The emulator exposes only allowlisted BRAIN commands.
- Arbitrary Android shell execution remains blocked.

## Runtime identity

- `BRAIN_RUNTIME=BRAIN_TERMUX_EMULATOR`
- `BRAIN_MODE=emulator`
- `BRAIN_PORT=8787`

The repository remains the source of truth. GitHub Actions builds and verifies the application; BRAIN Cloud Hub runs the services.
