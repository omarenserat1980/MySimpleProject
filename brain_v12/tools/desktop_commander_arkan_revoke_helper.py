#!/usr/bin/env python3
"""Electronic Brain helper for revoking the Arkan Desktop Commander device.

Important: Remote Desktop Commander's hosted device-revocation API is not exposed
by the installed connector/CLI. This helper opens the official dashboard and
provides a guarded checklist; it does NOT pretend to revoke a device itself.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser

DASHBOARD = "https://mcp.desktopcommander.app/"
TARGET_NAME = "arkan"
TARGET_ID = "645d5168-7f81-4290-868d-a4e8fabbc375"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--open-dashboard",
        action="store_true",
        help="Open the official Desktop Commander device-management dashboard.",
    )
    args = parser.parse_args()

    print("Electronic Brain — Desktop Commander device revocation helper")
    print(f"Target device: {TARGET_NAME}")
    print(f"Last known device ID: {TARGET_ID}")
    print()
    print("Guardrails:")
    print("  1. In Your Devices, select only 'arkan'.")
    print("  2. Choose the single-device 'Revoke' action.")
    print("  3. Do NOT choose 'Revoke All'.")
    print("  4. Re-list devices after revocation to verify the result.")
    print()
    print("No revocation API is exposed to this script, so it cannot revoke")
    print("the server-side authorization automatically or claim success.")
    print(f"Dashboard: {DASHBOARD}")

    if args.open_dashboard:
        opened = webbrowser.open(DASHBOARD)
        print("Browser open request:", "sent" if opened else "not confirmed")
    else:
        print("To open the dashboard, rerun with --open-dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
