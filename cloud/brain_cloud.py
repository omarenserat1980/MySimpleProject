import os
import signal
import subprocess
import time
from pathlib import Path

STOP=False

def stop(*_):
    global STOP
    STOP=True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

root=Path(__file__).resolve().parents[1]
interval=int(os.getenv("FACTORY_INTERVAL_SECONDS","21600"))

print("BRAIN_CLOUD_BOOT=1", flush=True)
print("BRAIN_CLOUD_MODE=provider-neutral", flush=True)
print(f"FACTORY_INTERVAL_SECONDS={interval}", flush=True)

while not STOP:
    env=os.environ.copy()
    env.setdefault("PYTHONPATH",str(root))
    env.setdefault("FACTORY_ALLOW_PRODUCTION","1")
    env.setdefault("FACTORY_REQUIRE_REAL_MEDIA","1")
    env.setdefault("FACTORY_ONE_SHOT","1")
    print("BRAIN_CLOUD_CYCLE_START=1", flush=True)
    try:
        p=subprocess.run(
            ["python","-m","brain_v7.braincore_v2.background_factory_worker"],
            cwd=root, env=env, timeout=max(interval,300)
        )
        print(f"BRAIN_CLOUD_CYCLE_EXIT={p.returncode}", flush=True)
    except subprocess.TimeoutExpired:
        print("BRAIN_CLOUD_CYCLE_TIMEOUT=1", flush=True)
    except Exception as exc:
        print(f"BRAIN_CLOUD_CYCLE_ERROR={type(exc).__name__}:{exc}", flush=True)
    if STOP:
        break
    for _ in range(interval):
        if STOP: break
        time.sleep(1)
print("BRAIN_CLOUD_STOP=1", flush=True)
