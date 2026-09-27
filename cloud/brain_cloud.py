import os
import signal
import subprocess
import time
from pathlib import Path

STOP = False

def stop(*_):
    global STOP
    STOP = True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

ROOT = Path(__file__).resolve().parents[1]
INTERVAL = int(os.getenv("FACTORY_INTERVAL_SECONDS", "21600"))
BACKOFF = int(os.getenv("BRAIN_FAILURE_BACKOFF_SECONDS", "60"))
MAX_BACKOFF = int(os.getenv("BRAIN_MAX_BACKOFF_SECONDS", "1800"))

print("BRAIN_CLOUD_BOOT=1", flush=True)
print("BRAIN_CLOUD_MODE=internet-connected", flush=True)
print("BRAIN_CLOUD_PUBLIC_WEB=1", flush=True)
print("BRAIN_SOFTWARE_FACTORY=1", flush=True)
print("BRAIN_GOAL_ORCHESTRATOR=1", flush=True)

def run_software_factory(env):
    try:
        return subprocess.run(
            ["python", "cloud/goal_engine.py"],
            cwd=ROOT, env=env, timeout=300
        ).returncode
    except Exception as exc:
        print(f"BRAIN_SOFTWARE_FACTORY_ERROR={type(exc).__name__}:{exc}", flush=True)
        return 1

failure_backoff = BACKOFF

while not STOP:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    env.setdefault("FACTORY_ALLOW_PRODUCTION", "1")
    env.setdefault("FACTORY_REQUIRE_REAL_MEDIA", "1")
    env.setdefault("FACTORY_ONE_SHOT", "1")
    env.setdefault("BRAIN_BLOCK_PRIVATE_NETWORKS", "1")
    env.setdefault("BRAIN_HTTP_TIMEOUT", "30")

    print("BRAIN_CLOUD_CYCLE_START=1", flush=True)
    factory_rc = run_software_factory(env)
    if factory_rc != 0:
        print(f"BRAIN_CLOUD_SOFTWARE_GATE=FAIL rc={factory_rc}", flush=True)
        for _ in range(failure_backoff):
            if STOP:
                break
            time.sleep(1)
        failure_backoff = min(failure_backoff * 2, MAX_BACKOFF)
        continue

    print("BRAIN_CLOUD_SOFTWARE_GATE=PASS", flush=True)
    try:
        result = subprocess.run(
            ["python", "-m", "brain_v7.braincore_v2.background_factory_worker"],
            cwd=ROOT,
            env=env,
            timeout=max(INTERVAL, 300),
        )
        print(f"BRAIN_CLOUD_CYCLE_EXIT={result.returncode}", flush=True)
        if result.returncode == 0:
            failure_backoff = BACKOFF
        else:
            print(f"BRAIN_CLOUD_RETRY_IN={failure_backoff}", flush=True)
            for _ in range(failure_backoff):
                if STOP:
                    break
                time.sleep(1)
            failure_backoff = min(failure_backoff * 2, MAX_BACKOFF)
            continue
    except subprocess.TimeoutExpired:
        print("BRAIN_CLOUD_CYCLE_TIMEOUT=1", flush=True)
    except Exception as exc:
        print(f"BRAIN_CLOUD_CYCLE_ERROR={type(exc).__name__}:{exc}", flush=True)

    for _ in range(INTERVAL):
        if STOP:
            break
        time.sleep(1)

print("BRAIN_CLOUD_STOP=1", flush=True)
