"""BRAIN Self-Test Matrix: one bounded, machine-readable health contract."""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GROUPS={
 "core":["brain_v12.tests.test_core","brain_v12.test_evidence_verification"],
 "autonomy":["brain_v12.tests.test_autonomy_control_plane","brain_v12.tests.test_brain_supervisor","brain_v12.brain.test_autonomous_reasoner"],
 "synchronization":["brain_v12.tests.test_sync_engine"],
 "repair":["brain_v12.brain.test_repair_engine","brain_v12.brain.test_repair_knowledge"],
 "self_healing":["brain_v12.self_healing.test_command_contract","brain_v12.self_healing.test_generator_registry","brain_v12.self_healing.test_improvement_eligibility","brain_v12.self_healing.test_native_patch_generator"],
 "tools_media":["brain_v12.tests.test_media_engine"],
 "tools_editor":["brain_v12.tests.test_quick_editor"],
 "tools_drawing":["brain_v12.tests.test_text_to_drawing"],
 "tools_player":["brain_v12.tests.test_video_player"],
 "tools_visual":["brain_v12.tests.test_visual_engine"],
 "runtime":["brain_v12.tests.test_runtime_contract","brain_v12.tests.test_operation_engine"],
}
def run_group(name,mods,timeout=90):
    started=time.time()
    cmd=[sys.executable,"-m","unittest",*mods,"-v"]
    try:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
        return {"group":name,"passed":p.returncode==0,"exit_code":p.returncode,"duration":round(time.time()-started,2),"stdout":p.stdout[-6000:],"stderr":p.stderr[-6000:]}
    except subprocess.TimeoutExpired:
        return {"group":name,"passed":False,"exit_code":124,"duration":round(time.time()-started,2),"error":"timeout"}
def main():
    results=[run_group(n,m) for n,m in GROUPS.items()]
    passed=all(x["passed"] for x in results)
    report={"schema":"brain-self-test-matrix/v1","status":"PASS" if passed else "FAIL","groups":results}
    out=ROOT/".brain/state/self_test_matrix.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for x in results:
        print(f"SELF_TEST_GROUP {x['group']}={'PASS' if x['passed'] else 'FAIL'}")
        if not x["passed"]:
            print(f"SELF_TEST_GROUP_DIAGNOSTIC {x['group']} stdout={x.get('stdout','')[-3000:]} stderr={x.get('stderr','')[-3000:]} error={x.get('error','')}")
    print(f"SELF_TEST_MATRIX={'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())
