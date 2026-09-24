import os
import time

from .brain.memory import MemoryStore
from .brain.render_monitor import RenderLogMonitor
from .brain.render_deploy_monitor import RenderDeployMonitor


def on_incident(incident):
    print(
        "RENDER_INCIDENT",
        incident.get("severity"),
        incident.get("fingerprint"),
        incident.get("message", "")[:1000],
        flush=True,
    )


def main():
    store = MemoryStore(os.getenv("BRAIN_DB", "brain_v12_monitor.db"))
    store.init()
    monitor = RenderLogMonitor(store, incident_callback=on_incident)
    deploy_monitor = RenderDeployMonitor(store)
    interval = max(monitor.poll_seconds, 10)
    while True:
        result = monitor.poll_once()
        deploy_result = deploy_monitor.poll_once()
        print(
            "RENDER_DEPLOY",
            deploy_result.get("status"),
            (deploy_result.get("latest") or {}).get("status", ""),
            flush=True,
        )
        print(
            "RENDER_MONITOR",
            result.get("status"),
            result.get("logs_seen", 0),
            len(result.get("incidents", [])),
            flush=True,
        )
        time.sleep(interval)


if __name__ == "__main__":
    main()
