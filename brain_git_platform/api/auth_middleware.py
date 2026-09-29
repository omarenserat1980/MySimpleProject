from __future__ import annotations
from .contracts import ApiResponse
from ..auth.authority import TokenAuthority

AUTHORITY=TokenAuthority()

def require_scope(headers: dict[str,str], scope: str) -> ApiResponse:
    value=headers.get("Authorization","")
    if not value.startswith("Bearer "): return ApiResponse(False,error="authentication_required")
    token=value[7:].strip()
    if not token or not AUTHORITY.verify(token,scope): return ApiResponse(False,error="forbidden")
    return ApiResponse(True,{"scope":scope})