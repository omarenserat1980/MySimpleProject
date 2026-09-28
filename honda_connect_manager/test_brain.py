import json
import tempfile
from pathlib import Path
from brain import load_vehicle_export, compatible, discover_exports

def test_export():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "update_by_usb.json"
        p.write_text(json.dumps({
            "systemVersion": "Honda CONNECT 3.0",
            "softwareVersion": "3.2.1",
            "hardwareVersion": "HW-01",
            "mcuVersion": "MCU-9",
            "packageName": "sample.zip",
            "sha256": "abc"
        }), encoding="utf-8")
        x = load_vehicle_export(p)
        assert x["software_version"] == "3.2.1"
        assert x["mcu_version"] == "MCU-9"
        assert x["package"] == "sample.zip"
        assert len(discover_exports(d)) == 1

def test_unknown_rules():
    ok, reason = compatible({"id": "youtube"}, "3.2.1")
    assert ok is None
    assert reason == "no compatibility rule"
