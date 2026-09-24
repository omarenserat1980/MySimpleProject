import os
import time
from typing import Optional

import httpx


class RenderDeployMonitor:
    """Read-only Render deployment supervisor.

    It observes the latest deployments and classifies the service state.
    It never triggers, cancels, or rolls back a deployment automatically.
    """

    TERMINAL_FAILURES = {"failed", "canceled", "cancelled", "deactivated"}
    ACTIVE = {"created", "build_in_progress", "update_in_progress", "live", "pending"}

    def __init__(self, store, service_id: Optional[str] = None, api_key: Optional[str] = None, poll_seconds: Optional[int] = None):
        self.store = store
        self.service_id = service_id or os.getenv("RENDER_SERVICE_ID", "")
        self.api_key = api_key or os.getenv("RENDER_API_KEY", "")
        self.poll_seconds = int(poll_seconds or os.getenv("RENDER_DEPLOY_POLL_SECONDS", os.getenv("RENDER_LOG_POLL_SECONDS", "60")))
        self.base_url = os.getenv("RENDER_API_BASE", "https://api.render.com/v1").rstrip("/")
        self.public_url = os.getenv("RENDER_PUBLIC_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")

    @property
    def configured(self):
        return bool(self.api_key and self.service_id)

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    def _fetch(self):
        response = httpx.get(
            f"{self.base_url}/services/{self.service_id}/deploys",
            headers=self._headers(),
            params={"limit": 20},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _items(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("deploys", "items", "data", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _status(self, item):
        return str(item.get("status") or item.get("state") or "").lower()

    def _commit(self, item):
        commit = item.get("commit") or {}
        if isinstance(commit, dict):
            return commit.get("id") or commit.get("sha") or commit.get("message")
        return str(commit) if commit else None

    def _summary(self, item):
        return {
            "id": item.get("id"),
            "status": self._status(item),
            "commit": self._commit(item),
            "created_at": item.get("createdAt") or item.get("created_at"),
            "updated_at": item.get("updatedAt") or item.get("updated_at"),
            "finished_at": item.get("finishedAt") or item.get("finished_at"),
            "trigger": item.get("trigger"),
            "reason": item.get("reason"),
            "service_id": self.service_id,
        }

    def poll_public_once(self):
        """Verify the deployed service from inside the brain without requiring Render secrets."""
        try:
            health = httpx.get(f"{self.public_url}/health", timeout=15).json()
            identity = httpx.get(f"{self.public_url}/api/deploy/identity", timeout=15).json()
            state = self.store.monitor_state()
            state.update({"public_last_poll": time.time(), "public_error": None, "public_ok": bool(health.get("ok")),
                          "public_version": health.get("version"), "public_commit": identity.get("commit"),
                          "public_service_id": identity.get("service_id")})
            self.store.set_monitor_state(state)
            self.store.event("RENDER_PUBLIC_HEALTH_CHECK", {"ok": state["public_ok"], "commit": state["public_commit"], "version": state["public_version"]})
            return {"ok": state["public_ok"], "status": "HEALTHY" if state["public_ok"] else "UNHEALTHY",
                    "version": state["public_version"], "commit": state["public_commit"], "service_id": state["public_service_id"]}
        except Exception as exc:
            state=self.store.monitor_state(); state.update({"public_last_poll":time.time(),"public_error":str(exc)[:1000],"public_ok":False}); self.store.set_monitor_state(state)
            self.store.event("RENDER_PUBLIC_HEALTH_FAILED", {"error":str(exc)[:1000]})
            return {"ok":False,"status":"PUBLIC_HEALTH_FAILED","error":str(exc)}

    def poll_once(self):
        if not self.configured:
            return {"ok": False, "status": "NOT_CONFIGURED", "required": ["RENDER_API_KEY", "RENDER_SERVICE_ID"]}

        try:
            items = self._items(self._fetch())
            latest = self._summary(items[0]) if items else None
            state = self.store.monitor_state()
            previous_id = state.get("deploy_id")
            status = latest.get("status") if latest else "NO_DEPLOYS"
            if latest:
                state.update({
                    "deploy_id": latest.get("id"),
                    "deploy_status": status,
                    "deploy_commit": latest.get("commit"),
                    "deploy_updated_at": latest.get("updated_at"),
                    "last_deploy_poll": time.time(),
                    "deploy_error": None,
                })
            else:
                state.update({"last_deploy_poll": time.time(), "deploy_error": None})
            self.store.set_monitor_state(state)

            if latest and latest.get("id") != previous_id:
                self.store.event("RENDER_DEPLOYMENT_CHANGED", latest)
            if status in self.TERMINAL_FAILURES:
                self.store.event("RENDER_DEPLOYMENT_FAILED", latest)

            return {
                "ok": True,
                "status": "COMPLETED",
                "service_id": self.service_id,
                "latest": latest,
                "deployments": [self._summary(x) for x in items[:20]],
                "action_policy": "OBSERVE_ONLY",
            }
        except Exception as exc:
            state = self.store.monitor_state()
            state.update({"last_deploy_poll": time.time(), "deploy_error": str(exc)})
            self.store.set_monitor_state(state)
            self.store.event("RENDER_DEPLOYMENT_POLL_FAILED", {"error": str(exc), "service_id": self.service_id})
            return {"ok": False, "status": "POLL_FAILED", "error": str(exc)}

    def status(self):
        state = self.store.monitor_state()
        return {
            "configured": self.configured,
            "service_id": self.service_id or None,
            "poll_seconds": self.poll_seconds,
            "last_poll": state.get("last_deploy_poll"),
            "last_error": state.get("deploy_error"),
            "latest": {
                "id": state.get("deploy_id"),
                "status": state.get("deploy_status"),
                "commit": state.get("deploy_commit"),
                "updated_at": state.get("deploy_updated_at"),
            },
            "action_policy": "OBSERVE_ONLY",
            "public_health": {"ok": state.get("public_ok"), "last_poll": state.get("public_last_poll"),
                              "version": state.get("public_version"), "commit": state.get("public_commit"),
                              "service_id": state.get("public_service_id"), "error": state.get("public_error")},
        }
