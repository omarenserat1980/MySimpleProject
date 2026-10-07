# Redmi → BRAIN Android Habitat bootstrap

Use this runbook on the Redmi/Termux node. It does not require root.

## 0. Repair the existing Termux:Boot chain

Before starting the Habitat, repair the older boot entries if they exist. The current Redmi may contain legacy launchers that reference a removed script such as `brain_v12/tools/termux_runtime_bootstrap.sh`.

From Termux:

```sh
cd ~/MySimpleProject
bash brain_android_habitat/repair_termux_boot.sh
```

This safely backs up the existing `~/.termux/boot/00-brain-runtime` and replaces it with the canonical Habitat entrypoint. It does not require root and does not bypass Android security.

## 1. Enter the Brain repository

```sh
cd ~/MySimpleProject
git checkout brain/android-habitat-v1
```

If the branch is not present locally:

```sh
git fetch origin brain/android-habitat-v1
git checkout brain/android-habitat-v1
```

## 2. Configure the Brain contract

```sh
export V12_AGENT_ID=redmi3-01
export V12_BRAIN_URL=http://127.0.0.1:8012
export V12_POLL_SECONDS=5
export V12_AGENT_KEY_FILE=$HOME/.brain/v12_agent.key
```

The key must already be provisioned by the Brain security contract. Do not paste or commit the key into Git.

## 3. Verify the local Brain API

```sh
curl -fsS http://127.0.0.1:8012/api/system/readiness
curl -fsS http://127.0.0.1:8012/api/media/health
```

Both responses must be healthy before starting the agent.

## 4. Start the existing Android bridge

```sh
python brain_emulator_agent/v12_agent.py
```

Expected first signal:

`[Brain-Termux] READY id=redmi3-01`

Then the agent sends heartbeat and polls the Brain task queue.

## 5. Readiness rule

The Redmi is not considered HABITAT READY merely because the agent prints READY. The Brain gate must verify identity, connectivity, runtime, writable habitat storage, permissions policy, and self-test.

## 6. Safety boundary

The Habitat is user-space only. It does not unlock the bootloader, obtain root, bypass Android permissions, or modify protected system partitions.

## 7. Recovery

If the network or Brain server disappears, stop treating the node as READY. The next Habitat Manager layer will add durable offline queue and restart/replay reconciliation.
