# PHONE-ONLY Android Executor v1

## Runtime layers

Brain API -> Foreground Executor -> Task Policy -> Android/File/Toybox adapters -> Verification -> Report.

## Safety boundary

The executor does not expose an unrestricted remote shell. Tasks are allowlisted and file paths are confined to the ElectronicBrain factory output root.

## Media pipeline

The next media adapter uses an app-private FFmpeg binary when supplied. It must be installed/bundled explicitly; the executor does not download executable binaries at runtime.

## Verification

A task returning exit code 0 is only execution success. The factory still needs artifact verification (existence, size, checksum and media-specific checks) before marking a production operation VERIFIED.

## Recovery

Transient failures use bounded exponential backoff. Persistent failures are reported to the Brain instead of looping indefinitely.
