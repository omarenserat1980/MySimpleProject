#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${1:-$HOME/MySimpleProject}"
OUT="${2:-$HOME/brain_blue_build_feasibility.json}"

python3 - "$ROOT" "$OUT" <<'PY'
import json, os, re, sys, time

root=os.path.abspath(sys.argv[1])
out=os.path.abspath(sys.argv[2])

candidates=[]
for rel in [
    "kernel", "kernel_xiaomi", "kernel_xiaomi_blue",
    "device", "device_xiaomi", "vendor", "vendor_xiaomi",
    "device/xiaomi/blue", "vendor/xiaomi/blue",
]:
    p=os.path.join(root, rel)
    if os.path.exists(p):
        candidates.append(p)

def walk_hits(base, names):
    hits=[]
    if not os.path.isdir(base): return hits
    for dp,dn,fn in os.walk(base):
        dn[:] = [d for d in dn if d not in {".git",".repo","out","build","node_modules"}]
        for n in fn:
            if n in names or any(x in n.lower() for x in ("blue","mt6765")):
                hits.append(os.path.relpath(os.path.join(dp,n),root))
        if len(hits)>=200: break
    return hits[:200]

result={
 "timestamp":time.time(),
 "safety":"read_only",
 "target":{"codename":"blue","model":"23129RN51X","hardware":"mt6765"},
 "source_root":root,
 "source_candidates":candidates,
 "evidence":{
   "defconfig_hits":walk_hits(root,{"defconfig","blue_defconfig","mt6765_defconfig"}),
   "device_tree_hits":walk_hits(root,{"Makefile","Kconfig","Android.bp","Android.mk"}),
   "blue_or_mt6765_hits":walk_hits(root,set())
 },
 "next_gate":"NEEDS_KERNEL_DEVICE_TREE_VENDOR_EVIDENCE"
}
if candidates:
    result["next_gate"]="SOURCE_PRESENT_SCAN_BUILD_CONFIGURATION"
with open(out,"w",encoding="utf-8") as f:
    json.dump(result,f,indent=2,sort_keys=True)
print(json.dumps(result,indent=2,sort_keys=True))
PY
