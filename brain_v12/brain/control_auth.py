import hmac
import os
from fastapi import HTTPException, Request

CONTROL_KEY_ENV = "BRAIN_CONTROL_KEY"

def require_control_key(request: Request) -> None:
    expected = os.getenv(CONTROL_KEY_ENV, "")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="CONTROL_PLANE_NOT_CONFIGURED",
        )
    supplied = request.headers.get("X-Brain-Control-Key", "")
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=403,
            detail="CONTROL_PLANE_AUTH_REQUIRED",
        )
