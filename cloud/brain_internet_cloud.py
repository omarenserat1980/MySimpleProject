import os
import signal
import subprocess
import time
from pathlib import Path

from internet_gateway import fetch

STOP = False
ROOT = Path(__file__).resolve().parents[1]
INTERVAL = int(os.getenv("FACTORY_INTERVAL_SECONDS", "21600"))
URLS = [u.strip() for u in os.getenv("BRAIN_PUBLIC_URLS", "").split(",") if u.strip()]

def stop(*_):
    global STOP
    STOP = True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

print("BRAIN_CLOUD_BOOT=1", flush=True)
print("BRAIN_INTERNET_ACCESS=public-http", flush=True)
print("BRAIN_PRIVATE_NETWORK_BLOCK=1", flush=True)

while not STOP:
    for url in URLS:
        try:
            result = fetch(url)
            print(f"INTERNET_FETCH status={result['status']} url={result['url']}", flush=True)
        except Exception as exc:
            print(f"INTERNET_FETCH_ERROR url={url} error={exc}", flush=True)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    env.setdefault("FACTORY_ALLOW_PRODUCTION", "1")
    env.setdefault("FACTORY_REQUIRE_REAL_MEDIA", "1")
    env.setdefault("FACTORY_ONE_SHOT", "1")

    print("BRAIN_CLOUD_CYCLE_START=1", flush=True)
    try:
        p = subprocess.run(
            ["python", "-m", "brain_v7.braincore_v2.background_factory_worker"],
            cwd=ROOT, env=env, timeout=max(INTERVAL, 300)
        )
        print(f"BRAIN_CLOUD_CYCLE_EXIT={p.returncode}", flush=True)
    except subprocess.TimeoutExpired:
        print("BRAIN_CLOUD_CYCLE_TIMEOUT=1", flush=True)
    except Exception as exc:
        print(f"BRAIN_CLOUD_CYCLE_ERROR={type(exc).__name__}:{exc}", flush=True)

    for _ in range(INTERVAL):
        if STOP:
            break
        time.sleep(1)

print("BRAIN_CLOUD_STOP=1", flush=True)
