"""Read-only Android/Termux connectivity probe for the Honda network project.

This probe never changes USB functions, tethering, routing, permissions, or firmware.
It records only non-secret interface and Android USB state metadata.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .memory import connect, initialize, DEFAULT_DB_PATH


def _run(command: list[str]) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=4
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()[:12000]


def collect_readonly_diagnostics() -> dict:
    """Collect safe, read-only facts available to an unprivileged Termux process."""
    props = {}
    for key in ("ro.build.version.release", "ro.product.model", "sys.usb.state",
                "persist.sys.usb.config", "ro.sys.usb.charging.only"):
        value = _run(["getprop", key])
        if value:
            props[key] = value

    interfaces = _run(["ip", "-brief", "link"])
    addresses = _run(["ip", "-brief", "address"])
    routes = _run(["ip", "route", "show"])
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "android_properties": props,
        "network_interfaces": interfaces,
        "network_addresses": addresses,
        "routes": routes,
        "limitations": [
            "This is a phone-side observation only; it cannot prove the head unit supports USB RNDIS host mode.",
            "Missing commands or denied properties are reported as unavailable, not as unsupported.",
            "No USB mode, tethering, route, setting, or firmware is changed.",
        ],
    }


def record_diagnostics(result: dict, db_path: str | Path | None = None) -> None:
    path = initialize(db_path)
    with connect(path) as db:
        usb_state = result.get("android_properties", {}).get("sys.usb.state", "unavailable")
        rndis_seen = "rndis" in usb_state.lower()
        db.execute(
            "INSERT INTO observations(topic,status,detail,source) VALUES(?,?,?,?)",
            ("phone_usb_probe", "observed",
             f"Read-only phone probe: USB state={usb_state}; RNDIS token present={rndis_seen}; "
             f"interfaces_available={result.get('network_interfaces') is not None}; "
             f"routes_available={result.get('routes') is not None}.",
             "Termux read-only diagnostics"),
        )
        db.execute(
            "INSERT INTO compatibility_checks(component,capability,result,evidence) VALUES(?,?,?,?)",
            ("Realme Android", "USB RNDIS gadget currently exposed",
             "supported" if rndis_seen else "not_tested",
             f"Observed sys.usb.state={usb_state}; phone-side only, head-unit host support not tested."),
        )
        db.execute(
            "INSERT INTO action_log(action,result,evidence) VALUES(?,?,?)",
            ("collect_readonly_diagnostics", "completed",
             "Read-only Termux probe; no system settings or USB modes changed."),
        )


def main() -> None:
    result = collect_readonly_diagnostics()
    record_diagnostics(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved read-only diagnostic record in Brain SQLite: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
