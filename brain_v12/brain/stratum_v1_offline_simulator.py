"""Deterministic offline Stratum V1 simulator for contract tests only.

This module performs no networking and never represents simulated shares as
accepted by a real pool.
"""
from __future__ import annotations
from typing import Any


class OfflineStratumSimulator:
    def __init__(self) -> None:
        self.authorized = False
        self.submitted_count = 0

    @staticmethod
    def _response(request: dict[str, Any], result: Any = None,
                  error: Any = None) -> dict[str, Any]:
        return {"id": request.get("id"), "result": result, "error": error,
                "simulated": True, "pool_acceptance_verified": False}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            return {"id": None, "result": None, "error": {"code": -32600, "message": "INVALID_REQUEST"},
                    "simulated": True, "pool_acceptance_verified": False}
        method = request.get("method")
        params = request.get("params")
        if not isinstance(params, list):
            return self._response(request, error={"code": -32600, "message": "INVALID_PARAMS"})
        if method == "mining.subscribe":
            return self._response(request, result=[[ ["mining.notify", "offline-session"] ], "offline-extranonce", 4])
        if method == "mining.authorize":
            self.authorized = bool(len(params) == 2 and params[0] == "sim.worker" and params[1] == "offline-placeholder")
            return self._response(request, result=self.authorized if self.authorized else False)
        if method == "mining.submit":
            if not self.authorized:
                return self._response(request, error={"code": 24, "message": "UNAUTHORIZED_SIMULATED_WORKER"})
            self.submitted_count += 1
            return self._response(request, result=True)
        return self._response(request, error={"code": -32601, "message": "METHOD_NOT_FOUND"})
