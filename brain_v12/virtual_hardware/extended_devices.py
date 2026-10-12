"""Software-only peripheral models for the Electronic Brain virtual machine.

These models are deterministic contracts and state machines, not physical devices.
They do not open host devices, allocate host hardware, access external networks, or
provide production cryptographic entropy. Timings, capacity, sensor values and power
values are modeled unless explicitly marked otherwise.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .ecc_memory import VirtualECCMemoryController


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class VirtualTPM:
    """A measured-boot/PCR contract; not a TPM command/firmware implementation."""
    pcr_count: int = 24
    pcrs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.pcr_count <= 0:
            raise ValueError("VTPM_PCR_COUNT_INVALID")
        if not self.pcrs:
            self.pcrs = ["0" * 64 for _ in range(self.pcr_count)]
        if len(self.pcrs) != self.pcr_count:
            raise ValueError("VTPM_PCR_STATE_INVALID")

    def extend(self, index: int, measurement: str) -> dict:
        if not 0 <= index < self.pcr_count or not isinstance(measurement, str) or not measurement:
            raise ValueError("VTPM_MEASUREMENT_INVALID")
        self.pcrs[index] = hashlib.sha256(bytes.fromhex(self.pcrs[index]) + measurement.encode()).hexdigest()
        return {"ok": True, "pcr": index, "digest": self.pcrs[index], "software_model": True,
                "hardware_attestation": False}

    def quote(self, indices: list[int] | None = None) -> dict:
        selected = list(range(self.pcr_count)) if indices is None else list(indices)
        if not selected or any(not isinstance(i, int) or i < 0 or i >= self.pcr_count for i in selected):
            raise ValueError("VTPM_QUOTE_SELECTION_INVALID")
        payload = {str(i): self.pcrs[i] for i in sorted(set(selected))}
        return {"selection": payload, "quote_digest": _json_digest(payload),
                "signed_by_hardware_key": False, "attestation_level": "software_simulation"}


@dataclass
class VirtualUSBController:
    port_count: int = 8
    supported_classes: tuple[str, ...] = ("hid", "storage", "serial", "audio", "camera")
    ports: dict[int, dict] = field(default_factory=dict)

    def attach(self, port: int, device_id: str, device_class: str) -> dict:
        if not device_id or device_class not in self.supported_classes:
            raise ValueError("VUSB_DEVICE_CLASS_UNSUPPORTED")
        if not 1 <= port <= self.port_count:
            raise ValueError("VUSB_PORT_OUT_OF_RANGE")
        if port in self.ports:
            raise RuntimeError("VUSB_PORT_OCCUPIED")
        self.ports[port] = {"device_id": device_id, "class": device_class, "state": "attached"}
        return {"ok": True, "port": port, **self.ports[port], "physical_usb_used": False}

    def detach(self, port: int) -> dict:
        if port not in self.ports:
            raise KeyError("VUSB_PORT_EMPTY")
        device = self.ports.pop(port)
        return {"ok": True, "port": port, "detached": device["device_id"]}

    def status(self) -> dict:
        return {"port_count": self.port_count, "ports_used": len(self.ports),
                "devices": {str(k): dict(v) for k, v in sorted(self.ports.items())},
                "physical_usb_used": False}


@dataclass
class VirtualSerialConsole:
    max_lines: int = 256
    lines: list[str] = field(default_factory=list)

    def write(self, text: str) -> dict:
        if not isinstance(text, str):
            raise TypeError("VSERIAL_TEXT_REQUIRED")
        self.lines.extend(text.splitlines() or ([text] if text else []))
        self.lines = self.lines[-self.max_lines:]
        return {"ok": True, "line_count": len(self.lines), "truncated_to_limit": True}

    def read(self, start: int = 0, limit: int = 100) -> list[str]:
        if start < 0 or limit < 0:
            raise ValueError("VSERIAL_RANGE_INVALID")
        return self.lines[start:start + limit]


@dataclass
class VirtualWatchdog:
    timeout_ticks: int = 10
    armed: bool = False
    remaining_ticks: int = 0
    expirations: int = 0

    def __post_init__(self) -> None:
        if self.timeout_ticks <= 0:
            raise ValueError("VWATCHDOG_TIMEOUT_INVALID")

    def arm(self) -> dict:
        self.armed, self.remaining_ticks = True, self.timeout_ticks
        return self.status()

    def feed(self) -> dict:
        if not self.armed:
            raise RuntimeError("VWATCHDOG_NOT_ARMED")
        self.remaining_ticks = self.timeout_ticks
        return self.status()

    def tick(self, ticks: int = 1) -> dict:
        if ticks < 0:
            raise ValueError("VWATCHDOG_TICKS_INVALID")
        expired = False
        if self.armed:
            self.remaining_ticks -= ticks
            if self.remaining_ticks <= 0:
                self.armed, self.remaining_ticks = False, 0
                self.expirations += 1
                expired = True
        return {**self.status(), "expired_now": expired, "reset_performed": False}

    def status(self) -> dict:
        return {"armed": self.armed, "remaining_ticks": self.remaining_ticks,
                "timeout_ticks": self.timeout_ticks, "expirations": self.expirations,
                "automatic_machine_reset": False}


@dataclass
class VirtualRNG:
    """Reproducible test bytes only; never use as cryptographic entropy."""
    seed: str = "brain-test-seed"
    counter: int = 0

    def bytes(self, count: int) -> bytes:
        if not 0 <= count <= 1_048_576:
            raise ValueError("VRNG_REQUEST_OUT_OF_RANGE")
        out = bytearray()
        while len(out) < count:
            out.extend(hashlib.sha256(f"{self.seed}:{self.counter}".encode()).digest())
            self.counter += 1
        return bytes(out[:count])

    def status(self) -> dict:
        return {"mode": "deterministic_test_rng", "counter": self.counter,
                "cryptographically_secure": False, "physical_rng_used": False}


@dataclass
class VirtualModem:
    technology: str = "5G"
    enabled: bool = False
    registered: bool = False
    connected: bool = False
    signal_dbm: int = -95
    apn: str | None = None
    simulated_bytes_tx: int = 0
    simulated_bytes_rx: int = 0

    def power(self, enabled: bool) -> dict:
        self.enabled = bool(enabled)
        if not self.enabled:
            self.registered = self.connected = False
        return self.status()

    def register(self, apn: str = "brain.test") -> dict:
        if not self.enabled:
            raise RuntimeError("VMODEM_POWERED_OFF")
        if not apn or self.signal_dbm < -120:
            raise RuntimeError("VMODEM_REGISTRATION_FAILED")
        self.apn, self.registered = apn, True
        return self.status()

    def connect(self) -> dict:
        if not self.registered:
            raise RuntimeError("VMODEM_NOT_REGISTERED")
        self.connected = True
        return self.status()

    def transmit(self, payload: bytes) -> dict:
        if not self.connected:
            raise RuntimeError("VMODEM_NOT_CONNECTED")
        size = len(payload)
        self.simulated_bytes_tx += size
        return {"ok": True, "bytes": size, "external_transmission": False,
                "network": "isolated-simulation"}

    def status(self) -> dict:
        return {"technology": self.technology, "enabled": self.enabled, "registered": self.registered,
                "connected": self.connected, "signal_dbm_estimate": self.signal_dbm, "apn": self.apn,
                "simulated_bytes_tx": self.simulated_bytes_tx, "simulated_bytes_rx": self.simulated_bytes_rx,
                "external_network_access": False, "radio_hardware_used": False}


@dataclass
class VirtualBMC:
    """Board-management controller contract with modeled sensors, fans and power supplies."""
    temperature_c: float = 35.0
    fan_rpm: int = 1800
    psu_count: int = 2
    psu_healthy: list[bool] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.psu_count <= 0:
            raise ValueError("VBMC_PSU_COUNT_INVALID")
        if not self.psu_healthy:
            self.psu_healthy = [True] * self.psu_count
        if len(self.psu_healthy) != self.psu_count:
            raise ValueError("VBMC_PSU_STATE_INVALID")

    def set_telemetry(self, temperature_c: float, fan_rpm: int) -> dict:
        if fan_rpm < 0 or temperature_c < -40 or temperature_c > 200:
            raise ValueError("VBMC_TELEMETRY_INVALID")
        self.temperature_c, self.fan_rpm = float(temperature_c), int(fan_rpm)
        event = {"event": "telemetry_update", "temperature_c_estimate": self.temperature_c, "fan_rpm": self.fan_rpm}
        self.events.append(event)
        return self.status()

    def set_psu(self, index: int, healthy: bool) -> dict:
        if not 0 <= index < self.psu_count:
            raise ValueError("VBMC_PSU_INDEX_INVALID")
        self.psu_healthy[index] = bool(healthy)
        self.events.append({"event": "psu_state", "index": index, "healthy": bool(healthy)})
        return self.status()

    def status(self) -> dict:
        return {"temperature_c_estimate": self.temperature_c, "fan_rpm_estimate": self.fan_rpm,
                "psu_healthy": list(self.psu_healthy), "redundancy_available": sum(self.psu_healthy) >= 2,
                "event_count": len(self.events), "physical_sensors_used": False}


@dataclass
class VirtualIOMMU:
    """Allow-list DMA isolation model; not hardware IOMMU enforcement."""
    mappings: dict[str, set[str]] = field(default_factory=dict)
    blocked_requests: int = 0

    def map(self, device_id: str, region: str) -> dict:
        if not device_id or not region:
            raise ValueError("VIOMMU_MAPPING_INVALID")
        self.mappings.setdefault(device_id, set()).add(region)
        return {"ok": True, "device_id": device_id, "region": region, "hardware_enforced": False}

    def dma_allowed(self, device_id: str, region: str) -> bool:
        allowed = region in self.mappings.get(device_id, set())
        if not allowed:
            self.blocked_requests += 1
        return allowed

    def status(self) -> dict:
        return {"device_mapping_count": len(self.mappings), "blocked_requests": self.blocked_requests,
                "hardware_enforced": False}


@dataclass
class VirtualRAID:
    """Logical RAID capacity/health model; does not create or persist block devices."""
    level: str = "1"
    member_capacities_bytes: list[int] = field(default_factory=lambda: [1 << 30, 1 << 30])
    member_healthy: list[bool] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.level not in {"0", "1", "5", "10"}:
            raise ValueError("VRAID_LEVEL_UNSUPPORTED")
        if not self.member_capacities_bytes or any(c <= 0 for c in self.member_capacities_bytes):
            raise ValueError("VRAID_MEMBER_CAPACITY_INVALID")
        minimum = {"0": 1, "1": 2, "5": 3, "10": 4}[self.level]
        if len(self.member_capacities_bytes) < minimum or (self.level == "10" and len(self.member_capacities_bytes) % 2):
            raise ValueError("VRAID_MEMBER_COUNT_INVALID")
        if not self.member_healthy:
            self.member_healthy = [True] * len(self.member_capacities_bytes)
        if len(self.member_healthy) != len(self.member_capacities_bytes):
            raise ValueError("VRAID_MEMBER_STATE_INVALID")

    @property
    def capacity_bytes(self) -> int:
        member = min(self.member_capacities_bytes)
        count = len(self.member_capacities_bytes)
        return {"0": member * count, "1": member, "5": member * (count - 1),
                "10": member * count // 2}[self.level]

    def set_member_health(self, index: int, healthy: bool) -> dict:
        if not 0 <= index < len(self.member_healthy):
            raise ValueError("VRAID_MEMBER_INDEX_INVALID")
        self.member_healthy[index] = bool(healthy)
        return self.status()

    def status(self) -> dict:
        healthy = sum(self.member_healthy)
        count = len(self.member_healthy)
        if self.level == "0":
            available = healthy == count
        elif self.level == "1":
            available = healthy >= 1
        elif self.level == "5":
            available = healthy >= count - 1
        else:
            available = all(self.member_healthy[i] or self.member_healthy[i ^ 1]
                            for i in range(0, count, 2))
        return {"level": self.level, "member_count": count, "healthy_members": healthy,
                "capacity_bytes": self.capacity_bytes, "available": available,
                "degraded": available and healthy < count, "persistent_block_storage": False}


@dataclass
class VirtualBattery:
    capacity_wh: float = 60.0
    state_of_charge: float = 1.0
    temperature_c: float = 25.0

    def __post_init__(self) -> None:
        if self.capacity_wh <= 0 or not 0 <= self.state_of_charge <= 1:
            raise ValueError("VBATTERY_CONFIGURATION_INVALID")

    def advance(self, load_watts_estimate: float, seconds: float) -> dict:
        if load_watts_estimate < 0 or seconds < 0:
            raise ValueError("VBATTERY_LOAD_INVALID")
        used_wh = load_watts_estimate * seconds / 3600.0
        self.state_of_charge = max(0.0, self.state_of_charge - used_wh / self.capacity_wh)
        return {"state_of_charge": self.state_of_charge, "estimated_energy_used_wh": used_wh,
                "load_watts_estimate": load_watts_estimate, "physical_measurement": False}


@dataclass
class VirtualInputDevice:
    queue_limit: int = 1024
    events: list[dict] = field(default_factory=list)

    def push(self, kind: str, code: str, value: int = 1) -> dict:
        if kind not in {"keyboard", "mouse", "touch"} or not code:
            raise ValueError("VINPUT_EVENT_INVALID")
        if len(self.events) >= self.queue_limit:
            raise RuntimeError("VINPUT_QUEUE_FULL")
        event = {"kind": kind, "code": code, "value": int(value), "sequence": len(self.events)}
        self.events.append(event)
        return {"ok": True, **event, "physical_input_used": False}

    def drain(self, limit: int = 100) -> list[dict]:
        if limit < 0:
            raise ValueError("VINPUT_DRAIN_LIMIT_INVALID")
        batch, self.events = self.events[:limit], self.events[limit:]
        return batch


@dataclass
class VirtualAudioDevice:
    sample_rate_hz: int = 48_000
    channels: int = 2
    frames_submitted: int = 0

    def submit_frames(self, frames: int) -> dict:
        if frames < 0 or self.sample_rate_hz <= 0 or self.channels <= 0:
            raise ValueError("VAUDIO_CONFIGURATION_INVALID")
        self.frames_submitted += frames
        return {"ok": True, "frames_submitted": frames, "duration_seconds_estimate": frames / self.sample_rate_hz,
                "sample_rate_hz": self.sample_rate_hz, "channels": self.channels,
                "physical_audio_output": False}


@dataclass
class VirtualSensorHub:
    values: dict[str, float] = field(default_factory=lambda: {"temperature_c": 35.0, "fan_rpm": 1800.0, "voltage_v": 12.0})

    def read(self, sensor: str) -> dict:
        if sensor not in self.values:
            raise KeyError("VSENSOR_UNKNOWN")
        return {"sensor": sensor, "value_estimate": self.values[sensor], "calibrated": False}

    def set_estimate(self, sensor: str, value: float) -> dict:
        if not sensor:
            raise ValueError("VSENSOR_NAME_INVALID")
        self.values[sensor] = float(value)
        return self.read(sensor)


class VirtualPeripheralFabric:
    """Convenience composition of common server, workstation, and connectivity peripherals."""
    def __init__(self) -> None:
        self.tpm = VirtualTPM()
        self.usb = VirtualUSBController()
        self.serial = VirtualSerialConsole()
        self.watchdog = VirtualWatchdog()
        self.rng = VirtualRNG()
        self.modem = VirtualModem()
        self.bmc = VirtualBMC()
        self.iommu = VirtualIOMMU()
        self.raid = VirtualRAID()
        self.battery = VirtualBattery()
        self.input = VirtualInputDevice()
        self.audio = VirtualAudioDevice()
        self.sensors = VirtualSensorHub()
        self.ecc_memory = VirtualECCMemoryController()

    def inventory(self) -> dict:
        return {
            "schema_version": 1,
            "mode": "SIMULATED",
            "host_hardware_required": False,
            "external_network_enabled": False,
            "devices": {
                "tpm": {"present": True, "fidelity": "software_measurement_contract", "hardware_attestation": False},
                "usb": {"present": True, "fidelity": "functional_port_and_enumeration_model"},
                "serial_console": {"present": True, "fidelity": "bounded_log_buffer"},
                "watchdog": {"present": True, "fidelity": "deterministic_tick_state_machine"},
                "rng": {"present": True, "fidelity": "deterministic_test_only"},
                "modem": {"present": True, "fidelity": "isolated_connectivity_state_machine"},
                "bmc": {"present": True, "fidelity": "modeled_telemetry_and_psu_state"},
                "iommu": {"present": True, "fidelity": "software_dma_allow_list"},
                "raid": {"present": True, "fidelity": "logical_capacity_and_health"},
                "battery": {"present": True, "fidelity": "energy_estimation"},
                "input": {"present": True, "fidelity": "event_queue"},
                "audio": {"present": True, "fidelity": "frame_accounting"},
                "sensors": {"present": True, "fidelity": "uncalibrated_estimates"},
                "ecc_memory": {"present": True, "fidelity": "functional_SECDED_single_bit_correction_double_bit_detection"},
            },
            "not_emulated": [
                "physical electrical signaling", "vendor firmware execution", "hardware-backed TPM keys",
                "cryptographically secure physical RNG", "real cellular radio/SIM registration",
                "host USB/audio/input access", "persistent RAID block devices", "hardware IOMMU enforcement",
            ],
        }

    def status(self) -> dict:
        return {"inventory": self.inventory(), "watchdog": self.watchdog.status(),
                "modem": self.modem.status(), "bmc": self.bmc.status(),
                "iommu": self.iommu.status(), "raid": self.raid.status(),
                "battery_state_of_charge": self.battery.state_of_charge,
                "ecc_memory": self.ecc_memory.status(),
                "usb": self.usb.status(), "physical_hardware_used": False}
