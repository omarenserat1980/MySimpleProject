from __future__ import annotations
import json
from pathlib import Path
from .service import AzureEmulator

def build_and_verify() -> dict:
    cloud = AzureEmulator(free_only=True)
    cloud.create_resource_group("brain-rg")
    cloud.create_network("brain-vnet")
    cloud.create_subnet("brain-subnet", "brain-vnet")
    cloud.create_public_ip("brain-ip")
    cloud.create_nic("brain-nic", "brain-subnet", "brain-ip")
    cloud.create_disk("brain-os", 64)
    cloud.create_windows_server_2025_vm("brain-win2025", vcpus=2, memory_mb=4096,
                                        storage_gb=64, nic="brain-nic")
    evidence = cloud.health_evidence("brain-win2025")
    if not evidence["ok"]:
        raise RuntimeError("EMULATOR_RELEASE_GATE_FAILED")
    return {"ok": True, "evidence": evidence, "state": cloud.export_state()}

def main() -> int:
    result = build_and_verify()
    out = Path(".brain/state/azure-emulator-evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "evidence": result["evidence"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
