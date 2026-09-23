"""Bounded external worker for the Electronic Brain.
Run this on a user-controlled host. It is not a ChatGPT background process.
"""
from __future__ import annotations
import os,time
from .autonomous_task import autonomous_task
from .autonomy_controller import build_plan
from .governance import append_audit
MAX_CYCLES=int(os.getenv("BRAIN_MAX_CYCLES","10"))
SLEEP_SECONDS=max(5,int(os.getenv("BRAIN_SLEEP_SECONDS","60")))
STOP_FILE=os.getenv("BRAIN_STOP_FILE","STOP_BRAIN")
def run(cycles:int=MAX_CYCLES)->dict:
    cycles=max(0,min(int(cycles),MAX_CYCLES)); completed=0
    for _ in range(cycles):
        if os.path.exists(STOP_FILE):
            append_audit("worker_stop",{"reason":"STOP_FILE"}); break
        plan=build_plan()
        result=autonomous_task.run("طور قدرات الدماغ واكتشف فرص ربح مشروعة",max_steps=12)
        append_audit("worker_cycle",{"plan":plan,"result_status":result.get("status")})
        completed+=1
        if completed<cycles: time.sleep(SLEEP_SECONDS)
    return {"status":"STOPPED" if os.path.exists(STOP_FILE) else "COMPLETED","cycles":completed}
if __name__=="__main__": print(run())
