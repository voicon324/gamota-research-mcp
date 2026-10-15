from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from .enums import ConfidenceLevel, RunStatus


def _value(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else value


def claim_confidence(
    *,
    is_valid: bool,
    freshness_findings: Iterable[str] = (),
    is_current: bool = False,
    independent_root_count: int = 0,
    has_unresolved_conflict: bool = False,
    has_relevant_not_comparable: bool = False,
    has_blocking_gap: bool = False,
) -> ConfidenceLevel:
    """Assign claim confidence only from validation, freshness and root independence."""
    if not is_valid:
        return ConfidenceLevel.INSUFFICIENT
    if any(finding in {"STALE_EVIDENCE", "FRESHNESS_UNKNOWN"} for finding in freshness_findings):
        return ConfidenceLevel.WEAK
    if has_unresolved_conflict:
        return ConfidenceLevel.WEAK
    if (
        is_current
        and independent_root_count >= 2
        and not has_relevant_not_comparable
        and not has_blocking_gap
    ):
        return ConfidenceLevel.STRONG
    return ConfidenceLevel.MODERATE


def run_confidence(status: RunStatus | str, claim_levels: Iterable[ConfidenceLevel | str]) -> ConfidenceLevel:
    status_value = _value(status)
    levels = [_value(level) for level in claim_levels]
    if status_value in {
        RunStatus.FAILED.value,
        RunStatus.NEEDS_CLARIFICATION.value,
        RunStatus.INSUFFICIENT_DATA.value,
    }:
        return ConfidenceLevel.INSUFFICIENT
    if status_value == RunStatus.PARTIAL.value or ConfidenceLevel.WEAK.value in levels:
        return ConfidenceLevel.WEAK
    if (
        status_value == RunStatus.COMPLETE.value
        and levels
        and all(level == ConfidenceLevel.STRONG.value for level in levels)
    ):
        return ConfidenceLevel.STRONG
    if ConfidenceLevel.MODERATE.value in levels:
        return ConfidenceLevel.MODERATE
    return ConfidenceLevel.INSUFFICIENT
