#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Safe, read-only discovery. No root, bootloader changes, flashing, or writes to /dev.
out="${1:-$HOME/brain_device_discovery.json}"
python3 - "$out" <<'PY'
import json, os, subprocess, sys, time

def cmd(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
    except Exception:
        return ""

def prop(name):
    return cmd("getprop", name)

def exists(path):
    return os.path.exists(path)

data = {
    "timestamp": time.time(),
    "safety": "read_only",
    "android": {
        "manufacturer": prop("ro.product.manufacturer"),
        "brand": prop("ro.product.brand"),
        "model": prop("ro.product.model"),
        "device": prop("ro.product.device"),
        "name": prop("ro.product.name"),
        "release": prop("ro.build.version.release"),
        "sdk": prop("ro.build.version.sdk"),
        "hardware": prop("ro.hardware"),
        "abi": prop("ro.product.cpu.abi"),
        "abis": prop("ro.product.cpu.abilist"),
    },
    "kernel": {
        "uname": cmd("uname", "-a"),
        "release": cmd("uname", "-r"),
        "version": cmd("uname", "-v"),
        "proc_version": cmd("cat", "/proc/version"),
        "proc_cmdline": cmd("cat", "/proc/cmdline"),
    },
    "boot_and_storage": {
        "boot_slot": prop("ro.boot.slot_suffix"),
        "verified_boot_state": prop("ro.boot.verifiedbootstate"),
        "flash_locked": prop("ro.boot.flash.locked"),
        "vbmeta_device": prop("ro.boot.vbmeta.device"),
        "super_partition": exists("/dev/block/by-name/super"),
        "boot_partition": exists("/dev/block/by-name/boot"),
        "vendor_boot_partition": exists("/dev/block/by-name/vendor_boot"),
        "init_boot_partition": exists("/dev/block/by-name/init_boot"),
        "vbmeta_partition": exists("/dev/block/by-name/vbmeta"),
    },
    "userspace": {
        "termux": exists("/data/data/com.termux"),
        "python": cmd("python3", "--version"),
        "uname_arch": cmd("uname", "-m"),
    }
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
print(json.dumps(data, indent=2, sort_keys=True))
PY
