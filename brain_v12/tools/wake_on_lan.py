#!/usr/bin/env python3
"""Electronic Brain Wake-on-LAN utility.

This sends a standard magic packet to a device on a reachable LAN. It does not
bypass BIOS/UEFI, NIC, router, firewall, or power-state requirements. By
default this tool only validates and previews the packet; pass --send to emit it.
"""
from __future__ import annotations

import argparse
import ipaddress
import re
import socket
import sys


MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$")


def normalize_mac(value: str) -> str:
    if not MAC_RE.fullmatch(value.strip()):
        raise argparse.ArgumentTypeError("MAC must look like AA:BB:CC:DD:EE:FF")
    return value.strip().replace("-", ":").lower()


def build_magic_packet(mac: str) -> bytes:
    raw = bytes.fromhex(mac.replace(":", ""))
    return b"\xff" * 6 + raw * 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or send a Wake-on-LAN magic packet to an authorized device."
    )
    parser.add_argument("--mac", required=True, type=normalize_mac,
                        help="target Ethernet MAC address")
    parser.add_argument("--broadcast", default="255.255.255.255",
                        help="LAN broadcast IPv4 address (default: 255.255.255.255)")
    parser.add_argument("--port", type=int, default=9, choices=range(1, 65536),
                        help="UDP destination port (default: 9)")
    parser.add_argument("--send", action="store_true",
                        help="actually send three UDP magic packets; omit for dry-run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        broadcast = str(ipaddress.IPv4Address(args.broadcast))
    except ipaddress.AddressValueError as exc:
        print(f"ERROR: invalid IPv4 broadcast address: {exc}", file=sys.stderr)
        return 2

    packet = build_magic_packet(args.mac)
    print("BRAIN_WOL_PREFLIGHT=PASS")
    print(f"TARGET_MAC={args.mac}")
    print(f"DESTINATION={broadcast}:{args.port}")
    print(f"PACKET_BYTES={len(packet)}")
    if not args.send:
        print("MODE=DRY_RUN")
        print("NEXT_STEP=Check BIOS/UEFI Wake-on-LAN, NIC power settings, and same-LAN reachability; rerun with --send to transmit.")
        return 0

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for _ in range(3):
                sent = sock.sendto(packet, (broadcast, args.port))
        print("BRAIN_WOL_SEND=OK")
        print(f"BYTES_SENT_PER_PACKET={sent}")
        print("WARNING=Packet transmission is not proof the computer powered on; verify device reachability or physical display.")
        return 0
    except OSError as exc:
        print(f"BRAIN_WOL_SEND=FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
