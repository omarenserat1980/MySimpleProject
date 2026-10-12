"""Software-only network hardware inventory and isolated packet-path simulator.

This is a deterministic logical model: it never opens sockets, controls host NICs,
emits RF, or forwards packets to an external network. Protocols are represented as
state/contracts unless explicitly described as packet-path behavior.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from ipaddress import ip_network
from typing import Any

NETWORK_DEVICE_KINDS = {
    "router": "Layer-3 routing state and logical forwarding",
    "switch_l2": "Layer-2 learning/forwarding state",
    "switch_l3": "Layer-2 switching plus logical Layer-3 routing",
    "firewall": "Ordered packet ACL evaluation",
    "access_point": "Wi-Fi SSID/channel/client state; no RF",
    "repeater": "Logical link extension; no RF",
    "bridge": "Logical Layer-2 bridge",
    "modem": "WAN link/registration state; no external connection",
    "ont": "Fiber ONT registration/link state; no optical hardware",
    "gateway": "Default-gateway/service state",
    "load_balancer": "Deterministic backend selection",
    "vpn_gateway": "Tunnel lifecycle metadata; no cryptographic tunnel",
    "dns_server": "Static hostname-to-address records",
    "dhcp_server": "Bounded simulated address leases",
    "ids": "Packet event observation; no signature database",
    "ips": "ACL-style simulated block action",
    "proxy": "Request metadata relay state; no external fetch",
    "nas": "Network storage service inventory; no persistent storage",
    "san_switch": "Storage-fabric zoning metadata",
    "poe_switch": "Modeled per-port PoE budget",
    "sdwan_edge": "Logical path/health policy",
    "cellular_base_station": "Registration and radio state only; no RF",
    "satellite_gateway": "Link budget/state estimate only; no RF",
    "network_tap": "Packet metadata copy counter",
    "packet_broker": "Packet metadata fan-out",
    "wan_optimizer": "Flow metadata and estimated compression only",
    "wireless_controller": "SSID/AP configuration metadata",
    "network_controller": "Topology/configuration inventory",
    "cable_modem": "DOCSIS-like link state; no RF or provider network",
    "optical_line_terminal": "PON subscriber inventory; no optical signaling",
    "media_converter": "Logical media conversion/link state",
    "transceiver": "Optics/transceiver inventory; no electrical/optical signaling",
    "nic": "Virtual endpoint and counters",
    "bonded_nic": "Logical link aggregation metadata",
    "network_card_rdma": "RDMA capability metadata only; no kernel bypass",
}

@dataclass
class NetworkDevice:
    device_id: str
    kind: str
    ports: int = 4
    vlan_ids: set[int] = field(default_factory=lambda: {1})
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    rx_packets: int = 0
    tx_packets: int = 0
    drops: int = 0

    def __post_init__(self):
        if not self.device_id or self.kind not in NETWORK_DEVICE_KINDS:
            raise ValueError("VNET_DEVICE_ID_OR_KIND_INVALID")
        if self.ports < 1 or not self.vlan_ids or any(v < 1 or v > 4094 for v in self.vlan_ids):
            raise ValueError("VNET_PORT_OR_VLAN_INVALID")

    def status(self) -> dict:
        return {"device_id": self.device_id, "kind": self.kind, "description": NETWORK_DEVICE_KINDS[self.kind],
                "ports": self.ports, "vlans": sorted(self.vlan_ids), "enabled": self.enabled,
                "rx_packets": self.rx_packets, "tx_packets": self.tx_packets, "drops": self.drops,
                "physical_hardware_used": False}

@dataclass
class NetworkLink:
    a: str
    b: str
    latency_ms_estimate: float = 0.1
    bandwidth_mbps_estimate: float = 1000.0
    vlan_ids: set[int] = field(default_factory=lambda: {1})
    enabled: bool = True

    def __post_init__(self):
        if self.a == self.b or self.latency_ms_estimate < 0 or self.bandwidth_mbps_estimate <= 0:
            raise ValueError("VNET_LINK_CONFIGURATION_INVALID")
        if not self.vlan_ids or any(v < 1 or v > 4094 for v in self.vlan_ids):
            raise ValueError("VNET_LINK_VLAN_INVALID")

class VirtualNetworkFabric:
    """Local-only topology, device inventory, ACLs, DHCP/DNS contracts and packet-path tests."""
    def __init__(self, *, packet_trace_limit: int = 512):
        if packet_trace_limit < 1:
            raise ValueError("VNET_TRACE_LIMIT_INVALID")
        self.devices: dict[str, NetworkDevice] = {}
        self.links: list[NetworkLink] = []
        self.firewall_rules: dict[str, list[dict]] = {}
        self.dns_records: dict[str, str] = {}
        self.dhcp_pools: dict[str, dict] = {}
        self.dhcp_leases: dict[str, str] = {}
        self.load_balancers: dict[str, list[str]] = {}
        self._lb_cursor: dict[str, int] = {}
        self.packet_trace_limit = packet_trace_limit
        self.trace: list[dict] = []

    def add_device(self, device_id: str, kind: str, *, ports: int = 4,
                   vlan_ids: set[int] | None = None, metadata: dict | None = None) -> dict:
        if device_id in self.devices:
            raise ValueError("VNET_DEVICE_DUPLICATE")
        dev = NetworkDevice(device_id, kind, ports, set(vlan_ids or {1}), True, dict(metadata or {}))
        self.devices[device_id] = dev
        if kind == "firewall":
            self.firewall_rules[device_id] = []
        return dev.status()

    def connect(self, a: str, b: str, *, latency_ms_estimate: float = 0.1,
                bandwidth_mbps_estimate: float = 1000.0, vlan_ids: set[int] | None = None) -> dict:
        if a not in self.devices or b not in self.devices:
            raise KeyError("VNET_LINK_ENDPOINT_UNKNOWN")
        if any({link.a, link.b} == {a, b} for link in self.links):
            raise ValueError("VNET_LINK_DUPLICATE")
        vlans = set(vlan_ids or (self.devices[a].vlan_ids & self.devices[b].vlan_ids))
        if not vlans or not vlans.issubset(self.devices[a].vlan_ids) or not vlans.issubset(self.devices[b].vlan_ids):
            raise ValueError("VNET_LINK_VLAN_MISMATCH")
        link = NetworkLink(a, b, float(latency_ms_estimate), float(bandwidth_mbps_estimate), vlans)
        self.links.append(link)
        return {"ok": True, "a": a, "b": b, "latency_ms_estimate": link.latency_ms_estimate,
                "bandwidth_mbps_estimate": link.bandwidth_mbps_estimate, "vlans": sorted(vlans)}

    def set_link(self, a: str, b: str, enabled: bool) -> dict:
        for link in self.links:
            if {link.a, link.b} == {a, b}:
                link.enabled = bool(enabled)
                return {"ok": True, "a": a, "b": b, "enabled": link.enabled}
        raise KeyError("VNET_LINK_UNKNOWN")

    def add_firewall_rule(self, device_id: str, *, action: str, protocol: str = "*",
                          src: str = "*", dst: str = "*", port: int | None = None) -> dict:
        if device_id not in self.firewall_rules:
            raise ValueError("VNET_FIREWALL_REQUIRED")
        if action not in {"allow", "deny"} or protocol not in {"*", "tcp", "udp", "icmp"}:
            raise ValueError("VNET_FIREWALL_RULE_INVALID")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("VNET_FIREWALL_PORT_INVALID")
        rule = {"action": action, "protocol": protocol.lower(), "src": src, "dst": dst, "port": port}
        self.firewall_rules[device_id].append(rule)
        return {"ok": True, "rule_index": len(self.firewall_rules[device_id]) - 1, **rule}

    @staticmethod
    def _matches(pattern: str, value: str) -> bool:
        if pattern == "*":
            return True
        try:
            return value in ip_network(pattern, strict=False)
        except ValueError:
            return pattern == value

    def _firewall_decision(self, device_id: str, packet: dict) -> str:
        for rule in self.firewall_rules.get(device_id, []):
            if (rule["protocol"] in {"*", packet["protocol"]} and
                self._matches(rule["src"], packet["src_ip"]) and
                self._matches(rule["dst"], packet["dst_ip"]) and
                (rule["port"] is None or rule["port"] == packet["dst_port"])):
                return rule["action"]
        return "allow"

    def send_packet(self, src: str, dst: str, *, vlan: int = 1, protocol: str = "tcp",
                    src_ip: str = "192.0.2.10", dst_ip: str = "192.0.2.20",
                    dst_port: int = 443, size_bytes: int = 512) -> dict:
        if src not in self.devices or dst not in self.devices:
            raise KeyError("VNET_PACKET_ENDPOINT_UNKNOWN")
        if vlan < 1 or vlan > 4094 or protocol.lower() not in {"tcp", "udp", "icmp"} or not 1 <= dst_port <= 65535 or size_bytes < 0:
            raise ValueError("VNET_PACKET_INVALID")
        if not self.devices[src].enabled or not self.devices[dst].enabled:
            return self._record({"ok": False, "reason": "endpoint_disabled", "path": []})
        queue = deque([(src, [src], 0.0, float("inf"))])
        visited = {src}
        found = None
        while queue:
            node, path, latency, bandwidth = queue.popleft()
            if node == dst:
                found = (path, latency, bandwidth)
                break
            for link in self.links:
                if not link.enabled or vlan not in link.vlan_ids:
                    continue
                neighbor = link.b if link.a == node else link.a if link.b == node else None
                if neighbor and neighbor not in visited and self.devices[neighbor].enabled and vlan in self.devices[neighbor].vlan_ids:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], latency + link.latency_ms_estimate,
                                  min(bandwidth, link.bandwidth_mbps_estimate)))
        if not found:
            self.devices[src].drops += 1
            return self._record({"ok": False, "reason": "no_path", "path": []})
        path, latency, bandwidth = found
        packet = {"protocol": protocol.lower(), "src_ip": src_ip, "dst_ip": dst_ip, "dst_port": dst_port}
        for hop in path:
            dev = self.devices[hop]
            if dev.kind == "firewall" and self._firewall_decision(hop, packet) == "deny":
                dev.drops += 1
                self.devices[src].tx_packets += 1
                return self._record({"ok": False, "reason": "firewall_denied", "path": path, "blocked_at": hop,
                                     "latency_ms_estimate": latency, "external_network_used": False})
        self.devices[src].tx_packets += 1
        self.devices[dst].rx_packets += 1
        for hop in path[1:-1]:
            self.devices[hop].rx_packets += 1
            self.devices[hop].tx_packets += 1
        result = {"ok": True, "reason": "delivered_in_simulation", "path": path, "vlan": vlan,
                  "protocol": protocol.lower(), "size_bytes": size_bytes, "latency_ms_estimate": latency,
                  "bandwidth_mbps_estimate": bandwidth, "external_network_used": False}
        return self._record(result)

    def configure_dns(self, hostname: str, address: str) -> dict:
        if not hostname or not address:
            raise ValueError("VNET_DNS_RECORD_INVALID")
        self.dns_records[hostname.rstrip(".").lower()] = address
        return {"ok": True, "hostname": hostname.rstrip(".").lower(), "address": address}

    def resolve_dns(self, hostname: str) -> dict:
        name = hostname.rstrip(".").lower()
        if name not in self.dns_records:
            return {"ok": False, "reason": "name_not_found", "hostname": name}
        return {"ok": True, "hostname": name, "address": self.dns_records[name], "external_dns_used": False}

    def configure_dhcp_pool(self, pool_id: str, network: str, *, first_host: int = 10, last_host: int = 200) -> dict:
        subnet = ip_network(network, strict=False)
        hosts = list(subnet.hosts())
        if not pool_id or first_host < 1 or last_host < first_host or last_host > len(hosts):
            raise ValueError("VNET_DHCP_POOL_INVALID")
        self.dhcp_pools[pool_id] = {"network": str(subnet), "first_host": first_host, "last_host": last_host}
        return {"ok": True, "pool_id": pool_id, **self.dhcp_pools[pool_id]}

    def dhcp_lease(self, pool_id: str, client_id: str) -> dict:
        if pool_id not in self.dhcp_pools or not client_id:
            raise ValueError("VNET_DHCP_REQUEST_INVALID")
        key = f"{pool_id}:{client_id}"
        if key in self.dhcp_leases:
            return {"ok": True, "client_id": client_id, "address": self.dhcp_leases[key], "reused": True}
        pool = self.dhcp_pools[pool_id]
        hosts = list(ip_network(pool["network"]).hosts())
        used = {v for k, v in self.dhcp_leases.items() if k.startswith(pool_id + ":")}
        for idx in range(pool["first_host"], pool["last_host"] + 1):
            candidate = str(hosts[idx - 1])
            if candidate not in used:
                self.dhcp_leases[key] = candidate
                return {"ok": True, "client_id": client_id, "address": candidate, "reused": False}
        return {"ok": False, "reason": "pool_exhausted"}

    def configure_load_balancer(self, lb_id: str, backends: list[str]) -> dict:
        if not lb_id or not backends or any(x not in self.devices for x in backends):
            raise ValueError("VNET_LB_BACKENDS_INVALID")
        self.load_balancers[lb_id] = list(backends)
        self._lb_cursor[lb_id] = 0
        return {"ok": True, "lb_id": lb_id, "backend_count": len(backends)}

    def select_backend(self, lb_id: str) -> dict:
        if lb_id not in self.load_balancers:
            raise KeyError("VNET_LB_UNKNOWN")
        backends = self.load_balancers[lb_id]
        for offset in range(len(backends)):
            idx = (self._lb_cursor[lb_id] + offset) % len(backends)
            if self.devices[backends[idx]].enabled:
                self._lb_cursor[lb_id] = (idx + 1) % len(backends)
                return {"ok": True, "backend": backends[idx], "algorithm": "round_robin_simulation"}
        return {"ok": False, "reason": "no_healthy_backend"}

    def inventory(self) -> dict:
        return {"schema_version": 1, "mode": "SIMULATED", "host_hardware_required": False,
                "external_network_enabled": False, "device_kind_count": len(NETWORK_DEVICE_KINDS),
                "device_kind_catalog": dict(NETWORK_DEVICE_KINDS),
                "devices": {key: dev.status() for key, dev in sorted(self.devices.items())},
                "links": [{"a": x.a, "b": x.b, "enabled": x.enabled, "vlans": sorted(x.vlan_ids),
                           "latency_ms_estimate": x.latency_ms_estimate,
                           "bandwidth_mbps_estimate": x.bandwidth_mbps_estimate} for x in self.links],
                "link_count": len(self.links), "dns_record_count": len(self.dns_records),
                "dhcp_pool_count": len(self.dhcp_pools), "dhcp_lease_count": len(self.dhcp_leases),
                "firewall_count": len(self.firewall_rules), "trace_count": len(self.trace),
                "physical_hardware_used": False}

    def _record(self, event: dict) -> dict:
        self.trace.append(dict(event))
        self.trace = self.trace[-self.packet_trace_limit:]
        return event
