"""
Response Envelope Utilities
===========================
Provides helpers to enforce a consistent response envelope across
WebSocket and REST layers without breaking existing payload semantics.

This module focuses on enrichment (adding missing metadata fields)
rather than strict transformation to preserve backwards compatibility
with existing tests and clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


DEFAULT_PROTOCOL_VERSION = "1.0"


@dataclass(frozen=True)
class EnvelopeMeta:
    version: str = DEFAULT_PROTOCOL_VERSION
    add_timestamp: bool = True


def ensure_envelope(message: Dict[str, Any],
                    request_id: Optional[str] = None,
                    meta: EnvelopeMeta = EnvelopeMeta()) -> Dict[str, Any]:
    """
    Ensure the message contains the standard envelope fields.

    Behavior:
    - Adds `version` if missing
    - Adds ISO `timestamp` if missing
    - Echoes `id` if provided and missing in message

    The function mutates a shallow copy of the input to avoid surprises.
    """
    if not isinstance(message, dict):
        # If message isn't a dict, pass through unchanged
        return message

    enriched = dict(message)  # shallow copy

    # Version
    if "version" not in enriched or not enriched.get("version"):
        enriched["version"] = meta.version

    # Timestamp
    if meta.add_timestamp and ("timestamp" not in enriched or not enriched.get("timestamp")):
        enriched["timestamp"] = datetime.now().isoformat()

    # Correlation id
    if request_id and ("id" not in enriched or not enriched.get("id")):
        enriched["id"] = request_id

    return enriched

