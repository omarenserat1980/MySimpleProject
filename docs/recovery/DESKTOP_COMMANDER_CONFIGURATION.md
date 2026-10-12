# Desktop Commander Configuration

## Current operational profile
- Device display name: localhost
- Platform: Android
- Desktop Commander version: 0.2.52
- Effective shell: /system/bin/sh
- Available shells observed: bash, /data/data/com.termux/files/usr/bin/bash, /bin/sh
- Python available to Desktop Commander runtime: no
- Node runtime: available
- Path separator: /
- Telemetry: enabled
- File read limit: 1000 lines
- File write limit: 50 lines
- Allowed directories: empty configuration

## Execution boundary
Desktop Commander can inspect and edit Termux files, but its Android runtime is not the Termux runtime. Direct execution of Termux Python/bash binaries can fail because of Android permission isolation.

Therefore:
- Desktop Commander: inspection, files, diagnostics and controlled editing.
- Actual Termux: Termux Python/bash execution when required.
- A Desktop Commander EACCES against a Termux binary does not prove Brain is dead.

## Confirmed paths
- /data/data/com.termux/files/home/MySimpleProject
- /data/data/com.termux/files/home/MySimpleProject/brain_v12/tools/brain_runtime_launcher.sh
- /data/data/com.termux/files/home/MySimpleProject/brain_v12/tools/brain_runtime_bootstrap.sh
- /data/data/com.termux/files/home/MySimpleProject/brain_v12/tools/brain_runtime_supervisor.py
- /data/data/com.termux/files/home/v12-agent/agent_config.sh

## Recovery rule
Desktop Commander configuration is operational metadata, not Brain state. A replacement device must recreate the documented access boundary, while Brain remains recoverable without the old installation.

Security note: command-blocking and access controls must be reviewed before changing Desktop Commander configuration.
