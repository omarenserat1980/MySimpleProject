"""Strict Stratum V1 subscribe-result validation; no session side effects."""
from __future__ import annotations
from typing import Any
import re

_HEX = re.compile(r"^[0-9a-fA-F]*$")

class SubscribeResultError(ValueError):
    """Malformed or untrusted subscribe response."""


def parse_subscribe_result(result: Any) -> dict[str, Any]:
    """Validate [subscriptions, extranonce1, extranonce2_size] without authorizing.

    Extranonce bytes are preserved as received. This parser does not infer pool
    byte order, open sockets, read credentials, or prove pool identity.
    """
    if not isinstance(result, list) or len(result) != 3:
        raise SubscribeResultError("INVALID_SUBSCRIBE_RESULT")
    subscriptions, extranonce1, extranonce2_size = result
    if not isinstance(subscriptions, list) or len(subscriptions) > 256:
        raise SubscribeResultError("INVALID_SUBSCRIPTIONS")
    for entry in subscriptions:
        if not isinstance(entry, list) or len(entry) != 2:
            raise SubscribeResultError("INVALID_SUBSCRIPTION_ENTRY")
        method, subscription_id = entry
        if (not isinstance(method, str) or not method or len(method) > 128
                or any(ord(c) < 32 for c in method)):
            raise SubscribeResultError("INVALID_SUBSCRIPTION_METHOD")
        if (not isinstance(subscription_id, str) or len(subscription_id) > 512
                or any(ord(c) < 32 for c in subscription_id)):
            raise SubscribeResultError("INVALID_SUBSCRIPTION_ID")
    if (not isinstance(extranonce1, str) or len(extranonce1) > 512
            or len(extranonce1) % 2 or not _HEX.fullmatch(extranonce1)):
        raise SubscribeResultError("INVALID_EXTRANONCE1")
    if (isinstance(extranonce2_size, bool) or not isinstance(extranonce2_size, int)
            or not 1 <= extranonce2_size <= 128):
        raise SubscribeResultError("INVALID_EXTRANONCE2_SIZE")
    return {
        "subscriptions": subscriptions,
        "extranonce1": extranonce1.lower(),
        "extranonce1_bytes": len(extranonce1) // 2,
        "extranonce2_size": extranonce2_size,
        "session_authorized": False,
        "pool_trust_verified": False,
        "source": "untrusted_stratum_subscribe_response",
    }
