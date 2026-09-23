"""Secret boundary: core code receives references, never raw credentials."""
from __future__ import annotations
def validate_reference(ref:str)->bool:
    # A provider reference is an opaque identifier, not a password/token.
    return bool(ref and len(ref)<=256 and "\n" not in ref and "\r" not in ref)
def reject_secret_like(value:str)->None:
    forbidden=("BEGIN PRIVATE KEY","sk_live_","password=","api_key=","secret=")
    if any(x.lower() in value.lower() for x in forbidden):
        raise ValueError("secret material must not enter the core")
