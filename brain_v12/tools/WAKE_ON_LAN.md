# Brain Wake-on-LAN tool


Use this utility from a device on the same reachable LAN as the target computer. It sends the standard UDP magic packet; it cannot power on a computer unless Wake-on-LAN is supported and enabled in firmware and the network adapter remains powered while the computer is off.

## Validate first (default: no network packet is sent)

```sh
python3 brain_v12/tools/wake_on_lan.py --mac AA:BB:CC:DD:EE:FF
```

## Send the packet

Only after replacing the example MAC with Arkan's actual Ethernet MAC and confirming Wake-on-LAN is enabled:

```sh
python3 brain_v12/tools/wake_on_lan.py --mac AA:BB:CC:DD:EE:FF --broadcast 192.168.1.255 --send
```

Use the broadcast address for the actual LAN; do not assume `192.168.1.255` is correct. Wi-Fi, VPNs, guest networks, router isolation, and internet/cloud hosts commonly prevent Wake-on-LAN from reaching the target. Do not expose UDP broadcast forwarding to the public internet.

## Evidence requirements

`BRAIN_WOL_SEND=OK` means only that the local operating system accepted the UDP packet for sending. It does not prove the target woke up. Confirm the computer becomes reachable, then separately verify Windows/VM boot. Never report success based on packet transmission alone.
