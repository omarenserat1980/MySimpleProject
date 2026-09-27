# PHONE-ONLY EXECUTOR

The image factory is now executor-agnostic.

## Modes

### 1. Direct Android/Termux
The factory executes a local generator directly.

```bash
export EB_EXECUTOR_MODE=direct
```

### 2. Generic Android terminal bridge
Any Android terminal/automation app that can expose a command can be used:

```bash
export EB_EXECUTOR_MODE=bridge
export EB_EXECUTOR_COMMAND='YOUR_EXECUTOR {payload}'
```

The placeholder `{payload}` receives JSON containing `argv` and `cwd`.

For simple command wrappers, `{argv}` is also available.

## Image generator

Set:

```bash
export EB_IMAGE_ADAPTER=/path/to/generator
```

The executor does not pretend that a generator exists. If none is available, the factory stops honestly and preserves state for resume.

## Probe

```bash
python -m cinematic_image_engine_v51.phone_executor_probe
```

This is the compatibility layer; it does not require a particular Android terminal application.
