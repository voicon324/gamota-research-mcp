from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .enums import (
    ClaimType,
    ClaimStatus,
    ConfidenceLevel,
    EvidenceRelation,
    IssueSeverity,
    IssueStatus,
    ProvenanceStatus,
    RunStatus,
    SourceMode,
    SourceType,
)


def new_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ResearchRun:
    question: str
    id: str = field(default_factory=new_id)
    status: RunStatus | str = RunStatus.CREATED
    created_at: str = field(default_factory=utc_now)
    finalized_at: str | None = None
    stop_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Source:
    run_id: str
    url: str
    id: str = field(default_factory=new_id)
    title: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    accessed_at: str = field(default_factory=utc_now)
    source_type: SourceType | str = SourceType.WEB
    parent_source_id: str | None = None
    root_source_id: str | None = None
    provenance_status: ProvenanceStatus | str = ProvenanceStatus.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    run_id: str
    source_id: str
    quote: str
    locator: str
    id: str = field(default_factory=new_id)
    root_source_id: str | None = None
    observed_at: str | None = None
    metric: str | None = None
    value: str | int | float | None = None
    unit: str | None = None
    market: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    scope: str | None = None
    method: str | None = None
    source_mode: SourceMode | str = SourceMode.LIVE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Claim:
    run_id: str
    text: str
    id: str = field(default_factory=new_id)
    claim_type: ClaimType | str = ClaimType.FACT
    status: ClaimStatus | str = ClaimStatus.PENDING
    confidence_level: ConfidenceLevel | str = ConfidenceLevel.UNASSESSED
    confidence_rationale: str | None = None
    target_metric: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    evidence_id: str
    relation: EvidenceRelation | str = EvidenceRelation.SUPPORTS


@dataclass(frozen=True)
class ResearchIssue:
    run_id: str
    code: str
    message: str
    id: str = field(default_factory=new_id)
    severity: IssueSeverity | str = IssueSeverity.WARNING
    status: IssueStatus | str = IssueStatus.OPEN
    related_claim_id: str | None = None
    source_id: str | None = None
    evidence_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
