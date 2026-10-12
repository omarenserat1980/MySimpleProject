# Arkan WSL — Electronic Brain internal runner setup

This guide addresses the production failure `BRAIN_INTERNAL_RUNNER_NOT_VERIFIED`.
It does **not** prove that Arkan is online, that the runner is registered, or that
the Brain API is healthy. Confirm each independently.

## 1. Open the correct shell

On Arkan, open **Ubuntu/WSL** (Linux shell), not Windows PowerShell and not Android
Termux. The production workflow requests a self-hosted **Linux x86-64** runner.

Check WSL from Windows PowerShell first, if needed:

```powershell
wsl --list --verbose
```

If no Ubuntu distribution is listed, install/configure WSL separately before
continuing. Do not run the following Bash commands in PowerShell.

## 2. Install and verify the required tools

From the Ubuntu/WSL shell, clone the repository if it is not already present, then run:

```bash
git clone https://github.com/omarenserat1980/MySimpleProject.git
cd MySimpleProject
bash brain_v12/tools/prepare_brain_internal_runner_wsl.sh
```

The default mode is read-only. If this is Ubuntu/Debian WSL and packages are missing,
install them explicitly:

```bash
bash brain_v12/tools/prepare_brain_internal_runner_wsl.sh --install
```

The installer uses `sudo apt-get` and installs QEMU, image/ISO utilities, FFmpeg,
Python, Git, and curl. Review the package list in the script before using `--install`.

## 3. Register a dedicated runner

In GitHub, open **Settings → Actions → Runners → New self-hosted runner** for this
repository. Follow GitHub's current Linux x64 instructions. Keep the temporary
registration token private; do not paste it into chat, commit it, or save it in the
repository.

When prompted for labels, use these custom labels:

```text
brain-internal,qemu,windows-real-boot
```

GitHub automatically supplies the standard `self-hosted`, `linux`, and `x64`
labels for a Linux runner. The workflow requires all six labels, so spelling matters.
Use a dedicated runner and do not run untrusted pull-request code on it.

## 4. Start the runner with the explicit local opt-in

For the initial test, start the runner in the foreground from its configured runner
directory. Do not start a second copy if one is already running.

```bash
BRAIN_INTERNAL_RUNNER_FLAG=1 ./run.sh
```

Keep that terminal open while testing. The flag is intentionally set in the runner
process environment, **not** in the GitHub workflow; setting it in workflow YAML would
turn the preflight into a self-assertion rather than a runner-side opt-in.

For unattended service operation, configure the same environment variable in the
runner's local systemd service override after the service has been installed. Find the
exact service name first:

```bash
systemctl list-units --type=service 'actions.runner*'
sudo systemctl edit <EXACT_RUNNER_SERVICE_NAME>
```

Add the following to the editor:

```ini
[Service]
Environment="BRAIN_INTERNAL_RUNNER_FLAG=1"
```

Then apply it and restart the exact service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart <EXACT_RUNNER_SERVICE_NAME>
sudo systemctl status <EXACT_RUNNER_SERVICE_NAME> --no-pager
```

Only do this for the dedicated, trusted runner you intend Brain to use. Do not put the
flag in repository secrets or workflow `env:` blocks.

## 5. Verify and rerun

1. Confirm the runner is **Online** in GitHub → Settings → Actions → Runners.
2. Run `bash brain_v12/tools/prepare_brain_internal_runner_wsl.sh` and confirm
   `RESULT: TOOLS_READY`.
3. Trigger the production workflow only after the runner has the required labels.
4. Check the run log for `BRAIN_INTERNAL_RUNNER=VERIFIED`, then confirm the independent
   artifact gate and uploaded MP4/manifest artifacts.

If the job remains queued, the runner is offline or its labels do not match. If preflight
fails, use the reported missing binaries or reasons; do not bypass the gate.

## Important limits

- WSL/tool readiness is not proof of the FastAPI API on port 8012; check that separately.
- This script does not register a runner, create a GitHub token, change Windows settings,
  boot a Windows Server VM, or launch a production job.
- A successful unit-test workflow on GitHub-hosted Ubuntu validates code, not Arkan's
  internal execution environment.
- Do not merge PR #424 or any other PR without the owner's explicit approval.
