from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_RESERVED_ASSURANCE_KEYS = frozenset({"source_assurance", "source_verification"})


def sanitize_untrusted_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Remove reserved assurance fields from caller-controlled metadata."""
    if not metadata:
        return {}
    return {
        key: value
        for key, value in metadata.items()
        if not isinstance(key, str) or key.casefold() not in _RESERVED_ASSURANCE_KEYS
    }


def source_assurance_for_host_supplied_source() -> dict[str, object]:
    """Describe what the server knows without claiming source verification."""
    return {
        "status": "NOT_INDEPENDENTLY_VERIFIED",
        "url_origin": "HOST_SUPPLIED",
        "quote_origin": "HOST_SUPPLIED",
        "source_retrieved_by_server": False,
        "message": (
            "The connected research agent supplied the source URL and quotation; "
            "the MCP server did not independently retrieve the source."
        ),
    }
