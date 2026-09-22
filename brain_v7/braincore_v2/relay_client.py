"""V11 Brain Relay client.

The Android brain never opens an inbound public port. It creates an outbound
HTTPS polling connection to a relay, receives one bounded task, executes it
through the existing autonomous task engine, and posts the result back.

Required environment:
  RELAY_URL=https://your-relay.example
  RELAY_TOKEN=<long-random-secret>
  RELAY_ID=android-brain-01

Optional:
  RELAY_POLL_SECONDS=5
  RELAY_TIMEOUT=30
"""
from __future__ import annotations
import os, time, socket
import httpx

from braincore_v2.autonomous_task import autonomous_task

RELAY_URL = os.getenv("RELAY_URL", "").rstrip("/")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")
RELAY_ID = os.getenv("RELAY_ID", socket.gethostname())
POLL_SECONDS = max(1, int(os.getenv("RELAY_POLL_SECONDS", "5")))
HTTP_TIMEOUT = max(5, int(os.getenv("RELAY_TIMEOUT", "30")))

def headers():
    return {
        "Authorization": f"Bearer {RELAY_TOKEN}",
        "X-Brain-ID": RELAY_ID,
        "Content-Type": "application/json",
    }

def run():
    if not RELAY_URL or not RELAY_TOKEN:
        print("Relay disabled: set RELAY_URL and RELAY_TOKEN to enable V11.")
        return

    print(f"Brain Relay enabled: {RELAY_URL} / {RELAY_ID}")
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        while True:
            try:
                r = client.get(
                    f"{RELAY_URL}/v1/tasks/next",
                    headers=headers(),
                    params={"brain_id": RELAY_ID},
                )
                r.raise_for_status()
                task = r.json()

                if task.get("task") is None:
                    time.sleep(POLL_SECONDS)
                    continue

                item = task["task"]
                task_id = item["id"]
                objective = str(item.get("objective", "")).strip()
                timeout = int(item.get("timeout", 30))
                max_steps = int(item.get("max_steps", 12))

                if not objective:
                    result = {"status": "FAILED", "reason": "OBJECTIVE_REQUIRED"}
                else:
                    result = autonomous_task.run(
                        objective,
                        timeout=max(1, min(timeout, 60)),
                        max_steps=max(1, min(max_steps, 12)),
                    )

                client.post(
                    f"{RELAY_URL}/v1/tasks/{task_id}/result",
                    headers=headers(),
                    json={"brain_id": RELAY_ID, "result": result},
                ).raise_for_status()

            except KeyboardInterrupt:
                print("Brain Relay stopped.")
                return
            except Exception as exc:
                print(f"Relay error: {exc}")
                time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    run()
