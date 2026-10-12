# Electronic Brain — Virtual Networking Hardware

## Scope

This is the initial software-only networking hardware layer for `brain_v12/virtual_hardware/network_hardware.py`. It inventories 36 network-device classes and supports an isolated logical topology. A catalog entry is not a claim of full vendor hardware or firmware emulation.

## Device inventory

- **Ethernet and switching:** NIC, bonded NIC/LAG, Layer-2 switch, Layer-3 switch, bridge, PoE switch, media converter, transceiver, network TAP, packet broker.
- **Routing and WAN:** router, gateway, modem, cable modem, fiber ONT, optical line terminal (OLT), SD-WAN edge, WAN optimizer.
- **Wireless and mobile:** Wi-Fi access point, repeater, wireless controller, cellular base station, satellite gateway.
- **Security and access:** firewall, IDS, IPS, VPN gateway, proxy, network controller.
- **Services and delivery:** DNS, DHCP, load balancer.
- **Storage and specialized fabrics:** NAS, SAN switch, RDMA-capability NIC metadata.

## Implemented behavior

- Create network nodes with VLAN membership and port inventory.
- Connect nodes with estimated latency/bandwidth, enforce VLAN compatibility, and inject link outages.
- Find a deterministic breadth-first packet path in a closed simulation, track counters and bounded packet outcomes.
- Evaluate ordered firewall allow/deny rules against protocol, source/destination and destination port.
- Maintain static DNS records, allocate deterministic DHCP leases, and select enabled load-balancer backends round-robin.
- Export an inspectable inventory with explicit simulation and isolation flags.

## Fidelity limits

- No host NIC binding, raw sockets, external network traffic, Wi-Fi/cellular/satellite RF, optical signaling, physical PoE, or physical-device control.
- Link bandwidth and latency are configured estimates; no cycle-accurate Ethernet/PHY, real routing protocol convergence, full TCP/IP stack, BGP/OSPF, DHCP/DNS wire protocol, NAT packet rewriting, VPN cryptography, IDS signatures, DOCSIS/PON firmware, RDMA kernel bypass, or vendor CLI/firmware are claimed.
- Firewall policy is a simplified ACL model. Packet forwarding is logical graph traversal, not a standards-complete switch/router implementation.
- The model must not be used as a security boundary for real systems.

## Verification

Run: `python -m unittest brain_v12.tests.test_network_hardware -v`

The GitHub Actions focused workflow also runs this suite. Passing tests validate only the declared model behaviors, not physical network compatibility.
