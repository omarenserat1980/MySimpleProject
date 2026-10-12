from __future__ import annotations

from .peripheral_profiles import get_motherboard_profile


class VirtualBus:
    """Virtual device topology, PCIe lane budgeting, DMA accounting and interrupt routing.

    This is a functional topology plus analytical bandwidth model, not PCIe protocol or
    electrical emulation. A lane allocation does not reserve or create host hardware.
    """
    def __init__(self, profile_id: str | None = None):
        self.profile = get_motherboard_profile(profile_id) if profile_id else None
        self.profile_id = profile_id
        self.devices = {}
        self.interrupts = []
        self.dma_transfers = []
        self.device_topology = {}
        self._next_fault = None
        self.stats = {"dma_transfers": 0, "dma_bytes": 0, "interrupts": 0,
                      "device_resets": 0, "hotplug_events": 0}

    def _requirements(self, name, device) -> dict:
        req = getattr(device, "bus_requirements", None)
        if callable(req):
            req = req()
        if not isinstance(req, dict):
            req = {"interface": "internal"}
        if name in {"cpu", "ram"}:
            return {"interface": "internal"}
        return dict(req)

    def attach(self, name, device):
        if name in self.devices:
            raise ValueError(f"DEVICE_ALREADY_ATTACHED:{name}")
        req = self._requirements(name, device)
        allocation = {"interface": req.get("interface", "internal"), "lanes": 0,
                      "sata_ports": 0, "requested_generation": req.get("generation"),
                      "negotiated_generation": None, "estimated_bandwidth_bytes_per_second": None}
        if self.profile and req.get("interface") == "pcie":
            lanes = int(req.get("lanes", 1))
            generation = int(req.get("generation", 1))
            used = sum(int(item["lanes"]) for item in self.device_topology.values())
            if lanes < 1 or used + lanes > self.profile.total_pcie_lanes:
                raise RuntimeError(f"BUS_PCIE_LANE_CONFLICT:{name}:used={used}:requested={lanes}:total={self.profile.total_pcie_lanes}")
            negotiated = min(generation, self.profile.pcie_generation)
            rate_gt_s = {1: 2.5, 2: 5.0, 3: 8.0, 4: 16.0, 5: 32.0}.get(negotiated, 2.5)
            bandwidth = rate_gt_s * 1_000_000_000 * (128 / 130) / 8 * lanes
            allocation.update({"lanes": lanes, "negotiated_generation": negotiated,
                               "estimated_bandwidth_bytes_per_second": int(bandwidth),
                               "bandwidth_is_analytical": True})
        elif self.profile and req.get("interface") == "sata":
            used = sum(int(item["sata_ports"]) for item in self.device_topology.values())
            ports = int(req.get("ports", 1))
            if used + ports > self.profile.sata_ports:
                raise RuntimeError(f"BUS_SATA_PORT_CONFLICT:{name}")
            allocation["sata_ports"] = ports
        self.devices[name] = device
        self.device_topology[name] = allocation
        self.stats["hotplug_events"] += 1
        return {"ok": True, "device": name, "topology": dict(allocation)}

    def detach(self, name):
        if name not in self.devices:
            return {"ok": False, "status": "DEVICE_NOT_ATTACHED", "device": name}
        self.devices.pop(name)
        self.device_topology.pop(name, None)
        self.stats["hotplug_events"] += 1
        return {"ok": True, "status": "DETACHED", "device": name, "virtual_hotplug": True}

    def reset_device(self, name):
        if name not in self.devices:
            raise KeyError("BUS_DEVICE_NOT_ATTACHED")
        device = self.devices[name]
        reset = getattr(device, "reset", None)
        if callable(reset):
            reset()
        else:
            for attr in ("tx_pending", "rx", "inflight", "command_queue"):
                value = getattr(device, attr, None)
                if isinstance(value, list):
                    value.clear()
                elif isinstance(value, dict):
                    value.clear()
        self.stats["device_resets"] += 1
        return {"ok": True, "device": name, "reset": True, "hardware_reset_claim": False}

    def inject_fault(self, fault: str):
        if fault not in {"dma_timeout", "interrupt_loss", "device_reset"}:
            raise ValueError(f"BUS_UNKNOWN_FAULT:{fault}")
        self._next_fault = fault
        return {"ok": True, "fault": fault, "deterministic": True}

    def dma_transfer(self, source: str, target: str, size_bytes: int):
        if size_bytes < 0:
            raise ValueError("BUS_DMA_SIZE_NEGATIVE")
        if source not in self.devices or target not in self.devices:
            raise KeyError("BUS_DMA_DEVICE_NOT_ATTACHED")
        fault = self._next_fault
        self._next_fault = None
        if fault == "dma_timeout":
            raise TimeoutError("BUS_DMA_INJECTED_TIMEOUT")
        if fault == "interrupt_loss":
            self.stats["interrupts"] += 1
            return {"ok": False, "status": "INTERRUPT_LOST", "source": source, "target": target}
        if fault == "device_reset":
            self.reset_device(target)
            raise RuntimeError("BUS_DMA_DEVICE_RESET")
        endpoints = [self.device_topology.get(name, {}) for name in (source, target)]
        rates = [int(item.get("estimated_bandwidth_bytes_per_second") or 0) for item in endpoints]
        available_rates = [rate for rate in rates if rate > 0]
        bandwidth = min(available_rates) if available_rates else 1_000_000_000
        estimated_seconds = size_bytes / max(1, bandwidth)
        record = {"source": source, "target": target, "size_bytes": size_bytes,
                  "estimated_bandwidth_bytes_per_second": bandwidth,
                  "estimated_seconds": estimated_seconds, "timing_is_estimated": True,
                  "data_bytes_copied": False, "host_dma_used": False}
        self.dma_transfers.append(record)
        self.stats["dma_transfers"] += 1
        self.stats["dma_bytes"] += size_bytes
        return {"ok": True, **record}

    def interrupt(self, source, payload=None, target="cpu"):
        fault = self._next_fault
        if fault == "interrupt_loss":
            self._next_fault = None
            self.stats["interrupts"] += 1
            return {"ok": False, "status": "INTERRUPT_LOST", "source": source}
        event = {"source": source, "target": target, "payload": payload or {},
                 "routed": target in self.devices, "delivery_model": "recorded_event_only"}
        self.interrupts.append(event)
        self.stats["interrupts"] += 1
        return event

    def enumerate_devices(self):
        return [{"name": name, "topology": dict(self.device_topology.get(name, {}))}
                for name in sorted(self.devices)]

    def validate_topology(self) -> dict:
        lanes = sum(int(item["lanes"]) for item in self.device_topology.values())
        sata_ports = sum(int(item["sata_ports"]) for item in self.device_topology.values())
        errors = []
        if self.profile and lanes > self.profile.total_pcie_lanes:
            errors.append("PCIE_LANE_BUDGET_EXCEEDED")
        if self.profile and sata_ports > self.profile.sata_ports:
            errors.append("SATA_PORT_BUDGET_EXCEEDED")
        return {"ok": not errors, "profile_id": self.profile_id,
                "pcie_lanes_total": self.profile.total_pcie_lanes if self.profile else None,
                "pcie_lanes_allocated": lanes, "pcie_lanes_free": self.profile.total_pcie_lanes - lanes if self.profile else None,
                "sata_ports_total": self.profile.sata_ports if self.profile else None,
                "sata_ports_allocated": sata_ports, "errors": errors,
                "fidelity": "functional_topology_and_approximate_bandwidth",
                "electrical_or_protocol_fidelity": False}

    def status(self) -> dict:
        return {"profile_id": self.profile_id, "devices": self.enumerate_devices(),
                "topology_validation": self.validate_topology(), "interrupts": list(self.interrupts),
                "dma": {"transfers": self.stats["dma_transfers"], "bytes": self.stats["dma_bytes"]},
                "stats": dict(self.stats), "physical_hardware_used": False}

    def device_names(self):
        return sorted(self.devices)
