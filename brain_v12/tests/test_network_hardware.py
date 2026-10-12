from __future__ import annotations
import unittest
from brain_v12.virtual_hardware.network_hardware import NETWORK_DEVICE_KINDS, VirtualNetworkFabric

class VirtualNetworkHardwareTests(unittest.TestCase):
    def test_catalog_covers_common_network_hardware(self):
        required = {"router","switch_l2","switch_l3","firewall","access_point","repeater","modem","ont",
                    "load_balancer","vpn_gateway","dns_server","dhcp_server","ids","ips","nas","san_switch",
                    "poe_switch","sdwan_edge","cellular_base_station","satellite_gateway","network_tap",
                    "wireless_controller","cable_modem","optical_line_terminal","transceiver","nic"}
        self.assertTrue(required.issubset(NETWORK_DEVICE_KINDS))
        fabric = VirtualNetworkFabric()
        self.assertFalse(fabric.inventory()["external_network_enabled"])

    def test_packet_forwarding_vlan_and_link_failure(self):
        f = VirtualNetworkFabric()
        f.add_device("host-a","nic",vlan_ids={10})
        f.add_device("sw1","switch_l2",vlan_ids={10})
        f.add_device("host-b","nic",vlan_ids={10})
        f.connect("host-a","sw1",vlan_ids={10},latency_ms_estimate=0.2)
        f.connect("sw1","host-b",vlan_ids={10},latency_ms_estimate=0.3)
        result=f.send_packet("host-a","host-b",vlan=10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["path"],["host-a","sw1","host-b"])
        self.assertAlmostEqual(result["latency_ms_estimate"],0.5)
        f.set_link("sw1","host-b",False)
        self.assertEqual(f.send_packet("host-a","host-b",vlan=10)["reason"],"no_path")

    def test_firewall_deny_rule(self):
        f=VirtualNetworkFabric()
        f.add_device("a","nic")
        f.add_device("fw","firewall")
        f.add_device("b","nic")
        f.connect("a","fw"); f.connect("fw","b")
        f.add_firewall_rule("fw",action="deny",protocol="tcp",dst="192.0.2.20",port=443)
        result=f.send_packet("a","b",dst_ip="192.0.2.20",dst_port=443)
        self.assertFalse(result["ok"])
        self.assertEqual(result["blocked_at"],"fw")

    def test_dns_dhcp_and_load_balancing(self):
        f=VirtualNetworkFabric()
        f.add_device("web1","nic"); f.add_device("web2","nic")
        f.configure_dns("brain.test","192.0.2.15")
        self.assertEqual(f.resolve_dns("BRAIN.TEST")["address"],"192.0.2.15")
        f.configure_dhcp_pool("lan","192.0.2.0/24",first_host=10,last_host=11)
        self.assertEqual(f.dhcp_lease("lan","client-a")["address"],"192.0.2.10")
        self.assertEqual(f.dhcp_lease("lan","client-b")["address"],"192.0.2.11")
        f.configure_load_balancer("web",["web1","web2"])
        self.assertEqual(f.select_backend("web")["backend"],"web1")
        f.devices["web1"].enabled=False
        self.assertEqual(f.select_backend("web")["backend"],"web2")

    def test_validation_and_no_physical_io(self):
        f=VirtualNetworkFabric()
        with self.assertRaisesRegex(ValueError,"VNET_DEVICE_ID_OR_KIND_INVALID"):
            f.add_device("bad","magic_router")
        f.add_device("a","nic"); f.add_device("b","nic")
        with self.assertRaisesRegex(ValueError,"VNET_LINK_DUPLICATE"):
            f.connect("a","b"); f.connect("b","a")
        self.assertFalse(f.inventory()["physical_hardware_used"])
        self.assertFalse(f.inventory()["external_network_enabled"])

if __name__ == "__main__":
    unittest.main()
