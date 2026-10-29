"""Portable logical expiry for records written through the public memory facade."""

import math
import time
from typing import Any

EXPIRY_FIELD = "_nexamem_expires_at"


def retained_metadata(metadata: dict[str, Any] | None, ttl_sec: int | None) -> dict[str, Any]:
    """Copy metadata and persist an absolute expiry without changing caller data."""
    result = dict(metadata or {})
    if EXPIRY_FIELD in result:
        raise ValueError(f"{EXPIRY_FIELD} is reserved for NexaMem retention")
    if ttl_sec is not None:
        if ttl_sec <= 0:
            raise ValueError("ttl_sec must be positive")
        result[EXPIRY_FIELD] = time.time() + ttl_sec
    return result


def expired(record: dict[str, Any]) -> bool:
    """Treat invalid persisted expiry values as expired rather than exposing content."""
    metadata = record.get("metadata", {})
    if EXPIRY_FIELD not in metadata:
        return False
    value = metadata[EXPIRY_FIELD]
    return not isinstance(value, (int, float)) or not math.isfinite(value) or value <= time.time()
