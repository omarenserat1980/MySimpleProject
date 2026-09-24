import os
import time

from .brain.memory import MemoryStore
from .brain.render_monitor import RenderLogMonitor
from .brain.render_deploy_monitor import RenderDeployMonitor
from brain_v7.braincore_v2.code_workspace_tool import CodeWorkspaceTool


def on_incident(incident):
    severity = incident.get("severity", "")
    print(
        "RENDER_INCIDENT",
        severity,
        incident.get("fingerprint"),
        incident.get("message", "")[:1000],
        flush=True,
    )

    # Read-only audit on new ERROR/CRITICAL incidents. Never changes source code.
    if severity in {"ERROR", "CRITICAL"}:
        try:
            workspace = CodeWorkspaceTool(
                root=os.getenv(
                    "BRAIN_CODE_ROOT",
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                ),
                allowed_prefixes=("brain_v7/", "brain_v12/"),
            )
            audit = workspace.verify([])
            print(
                "RENDER_CODE_AUDIT",
                audit.get("status"),
                "checked=" + str(audit.get("checked", 0)),
                "errors=" + str(audit.get("errors", []))[:3000],
                flush=True,
            )
        except Exception as exc:
            print("RENDER_CODE_AUDIT_FAILED", str(exc)[:2000], flush=True)


def main():
    store = MemoryStore(os.getenv("BRAIN_DB", "brain_v12_monitor.db"))
    store.init()
    monitor = RenderLogMonitor(store, incident_callback=on_incident)
    deploy_monitor = RenderDeployMonitor(store)
    interval = max(monitor.poll_seconds, 10)
    while True:
        result = monitor.poll_once()
        public_result = deploy_monitor.poll_public_once()
        deploy_result = deploy_monitor.poll_once()
        print(
            "RENDER_PUBLIC",
            public_result.get("status"),
            public_result.get("commit",""),
            flush=True,
        )
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
