from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


_REQUIRED_DIMENSIONS = (
    "metric",
    "unit",
    "market",
    "period_start",
    "period_end",
)
_OPTIONAL_DIMENSIONS = (
    "platform",
    "store",
    "genre_segment",
    "comparison_basis",
    "sample_scope",
)


@dataclass(frozen=True)
class ComparabilityResult:
    comparable: bool
    reasons: tuple[str, ...]
    signature: dict[str, str | None]


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _normalized(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().casefold().split())
    return normalized or None


def normalize_metric(value: Any) -> str | None:
    """Normalize metric identity without inferring semantic relationships."""
    normalized = _normalized(value)
    if normalized is None:
        return None
    return "_".join(normalized.replace("-", " ").split())


def _metadata(record: Any) -> Mapping[str, Any]:
    value = _get(record, "metadata", {})
    return value if isinstance(value, Mapping) else {}


def _optional_value(record: Any, dimension: str) -> Any:
    metadata = _metadata(record)
    if dimension in {"platform", "store", "comparison_basis"}:
        return metadata.get(dimension)
    if dimension == "genre_segment":
        return metadata.get("genre") or metadata.get("segment") or metadata.get("genre_segment")
    if dimension == "sample_scope":
        return (
            metadata.get("sample_scope")
            or metadata.get("population")
            or metadata.get("sample")
            or _get(record, "scope")
        )
    return None


def comparison_signature(record: Any) -> dict[str, str | None]:
    """Return the normalized dimensions that determine direct comparability."""
    signature = {
        dimension: _normalized(_get(record, dimension))
        for dimension in _REQUIRED_DIMENSIONS
    }
    signature.update(
        {
            dimension: _normalized(_optional_value(record, dimension))
            for dimension in _OPTIONAL_DIMENSIONS
        }
    )
    return signature


def compare_evidence(first: Any, second: Any) -> ComparabilityResult:
    """Conservatively determine whether two observations measure the same scope."""
    left = comparison_signature(first)
    right = comparison_signature(second)
    reasons: list[str] = []

    for dimension in _REQUIRED_DIMENSIONS:
        left_value = left[dimension]
        right_value = right[dimension]
        if left_value is None or right_value is None:
            reasons.append(f"missing_{dimension}")
        elif left_value != right_value:
            reasons.append(f"{dimension}_mismatch")

    for dimension in _OPTIONAL_DIMENSIONS:
        left_value = left[dimension]
        right_value = right[dimension]
        if left_value is None and right_value is None:
            continue
        if left_value is None or right_value is None:
            reasons.append(f"missing_{dimension}")
        elif left_value != right_value:
            reasons.append(f"{dimension}_mismatch")

    merged_signature = {
        dimension: left[dimension] if left[dimension] == right[dimension] else None
        for dimension in (*_REQUIRED_DIMENSIONS, *_OPTIONAL_DIMENSIONS)
    }
    return ComparabilityResult(
        comparable=not reasons,
        reasons=tuple(reasons),
        signature=merged_signature,
    )
