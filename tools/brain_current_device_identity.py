#!/usr/bin/env python3
"""Read-only identity probe for the device where this script is executed.

Prints non-secret runtime identity facts. It never prints environment-variable
values, tokens, keys, serial numbers, IP addresses, or full filesystem paths.
"""
from __future__ import annotations

import os
import platform
import socket
import sys


def present(name: str) -> bool:
    value = os.environ.get(name)
    return bool(value and value.strip())


def main() -> int:
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    android_markers = {
        "ANDROID_ROOT": present("ANDROID_ROOT"),
        "ANDROID_DATA": present("ANDROID_DATA"),
        "TERMUX_VERSION": present("TERMUX_VERSION"),
        "PREFIX_contains_com.termux": "com.termux" in os.environ.get("PREFIX", "").lower(),
    }
    is_android = system.lower() == "android" or any(android_markers.values())
    if is_android and any(android_markers.values()):
        device_class = "Android / likely Termux"
    elif is_android:
        device_class = "Android (Termux not confirmed)"
    elif system == "Windows":
        device_class = "Windows computer"
    elif system == "Darwin":
        device_class = "macOS computer"
    elif system == "Linux":
        device_class = "Linux computer / server (not identified as Android)"
    else:
        device_class = "Unknown / other runtime"

    print("BRAIN_CURRENT_DEVICE_IDENTITY")
    print(f"device_class={device_class}")
    print(f"os={system or 'unknown'}")
    print(f"os_release={release or 'unknown'}")
    print(f"architecture={machine or 'unknown'}")
    print(f"hostname_available={'yes' if socket.gethostname() else 'no'}")
    print(f"python_version={platform.python_version()}")
    print(f"python_executable_available={'yes' if sys.executable else 'no'}")
    print("android_termux_markers:")
    for name, found in android_markers.items():
        print(f"  {name}={'present' if found else 'absent'}")
    print("brain_agent_environment_names_present (values hidden):")
    for name in (
        "V12_BRAIN_URL",
        "V12_AGENT_ID",
        "V12_AGENT_KEY_FILE",
        "BRAIN_EMULATOR_KEY",
        "BRAIN_EMULATOR_KEY_FILE",
        "X_V12_AGENT_KEY",
    ):
        print(f"  {name}={'present' if present(name) else 'absent'}")
    print("network_access_tested=no")
    print("device_bridge_auth_tested=no")
    print("interpretation=This identifies only the environment where this script ran; it cannot identify a phone that is not connected to this session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
