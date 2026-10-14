#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
OUT="${ASIC_EVIDENCE_DIR:-$ROOT/artifacts/asic}"
mkdir -p "$OUT"

fail() { echo "ASIC_HEALTHCHECK_FAIL: $*" >&2; exit 1; }
need_file() { [[ -s "$1" ]] || fail "REQUIRED_FILE_MISSING:$1"; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || fail "REQUIRED_TOOL_MISSING:$1"; }

echo "[1/6] Checking internal ASIC components"
need_file brain_v12/asic/rtl/brain_asic_core.sv
need_file brain_v12/asic/rtl/tb_brain_asic_core.sv
need_file brain_v12/asic/rtl/brain_asic_core_tb.sv
need_file brain_v12/asic/toolchain_probe.py
need_file brain_v12/brain/asic_hardware_simulator.py
need_file brain_v12/tests/test_asic_hardware_simulator.py
echo "ASIC_COMPONENT_INVENTORY_PASS"

echo "[2/6] Recording toolchain versions"
python -m brain_v12.asic.toolchain_probe | tee "$OUT/toolchain.json"
need_cmd iverilog
need_cmd vvp
need_cmd yosys
python - <<'PY' "$OUT/toolchain.json"
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for tool in ("iverilog", "verilator", "yosys"):
    item = data["tools"][tool]
    print(f"TOOL {tool}: {item['status']} {item.get('version') or ''}")
if data["tools"]["iverilog"]["status"] != "AVAILABLE":
    raise SystemExit("IVERILOG_NOT_AVAILABLE")
if data["tools"]["yosys"]["status"] != "AVAILABLE":
    raise SystemExit("YOSYS_NOT_AVAILABLE")
PY

echo "[3/6] Running RTL testbench A"
iverilog -g2012 -Wall -s tb_brain_asic_core \
  -o "$OUT/tb_brain_asic_core.vvp" \
  brain_v12/asic/rtl/brain_asic_core.sv \
  brain_v12/asic/rtl/tb_brain_asic_core.sv
vvp "$OUT/tb_brain_asic_core.vvp" | tee "$OUT/rtl-selftest.log"
grep -q "ALL_RTL_TESTS_PASSED" "$OUT/rtl-selftest.log"

echo "[4/6] Running RTL testbench B"
iverilog -g2012 -Wall -s brain_asic_core_tb \
  -o "$OUT/brain_asic_core_tb.vvp" \
  brain_v12/asic/rtl/brain_asic_core.sv \
  brain_v12/asic/rtl/brain_asic_core_tb.sv
vvp "$OUT/brain_asic_core_tb.vvp" | tee "$OUT/rtl-boundary-test.log"
grep -q "ASIC_RTL_TB_PASS" "$OUT/rtl-boundary-test.log"

echo "[5/6] Running software-model regression"
python -m pytest brain_v12/tests/test_asic_hardware_simulator.py -q \
  | tee "$OUT/software-model-tests.log"
grep -Eq "[0-9]+ passed" "$OUT/software-model-tests.log"

echo "[6/6] Synthesizing RTL and checking design"
yosys -p "read_verilog -sv brain_v12/asic/rtl/brain_asic_core.sv; hierarchy -top brain_asic_core; proc; opt; check; stat; write_json $OUT/brain_asic_core.json" \
  2>&1 | tee "$OUT/yosys-synthesis.log"
grep -Eq "Found and reported 0 problems|Number of problems: 0" "$OUT/yosys-synthesis.log"

python - <<'PY' "$OUT"
import hashlib, json, os, subprocess, sys, time
out = sys.argv[1]
files = [
    "brain_v12/asic/rtl/brain_asic_core.sv",
    "brain_v12/asic/rtl/tb_brain_asic_core.sv",
    "brain_v12/asic/rtl/brain_asic_core_tb.sv",
    "brain_v12/asic/toolchain_probe.py",
    "brain_v12/brain/asic_hardware_simulator.py",
    "brain_v12/tests/test_asic_hardware_simulator.py",
]
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
checks = {
    "component_inventory": "PASS",
    "toolchain_versions": "PASS",
    "rtl_testbench_a": "PASS",
    "rtl_testbench_b": "PASS",
    "software_model_tests": "PASS",
    "yosys_synthesis_check": "PASS",
}
manifest = {
    "schema_version": 1,
    "created_at_unix": time.time(),
    "commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
    "checks": checks,
    "source_sha256": {p: sha(p) for p in files},
    "evidence_files": sorted(os.listdir(out)),
    "physical_asic_present_or_verified": False,
    "claim": "RTL_SIMULATION_AND_GENERIC_SYNTHESIS_ONLY; NOT_PHYSICAL_SILICON_VERIFICATION",
}
with open(os.path.join(out, "health-manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
print(json.dumps(manifest, indent=2, sort_keys=True))
print("ASIC_INTERNAL_COMPONENTS_HEALTHCHECK_PASS")
PY
