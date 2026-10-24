from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from enum import Enum
from uuid import NAMESPACE_URL, uuid5

from .comparability import compare_evidence, normalize_metric
from .confidence import claim_confidence, run_confidence
from .enums import (
    ClaimStatus,
    ConfidenceLevel,
    IssueSeverity,
    IssueStatus,
    RunStatus,
    StopReason,
)
from .models import Claim, ResearchIssue, utc_now
from .repository import ResearchRepository


_NUMBER_RE = re.compile(
    r"(?<![\w.])(?P<currency>[$€£₫])?\s*"
    r"(?P<number>\d+(?:[.,]\d+)*)\s*"
    r"(?P<unit>%|percent(?:age)?|downloads?|installs?|users?|usd|eur|vnd|gbp|"
    r"dau|mau|million|billion|thousand|k|m|x|times?)?(?![\w%])",
    re.IGNORECASE,
)
_CURRENCY_CODES = {"$": "USD", "€": "EUR", "£": "GBP", "₫": "VND"}
_PERCENT_UNITS = {"%", "percent", "percentage"}


def _value(value):
    return value.value if isinstance(value, Enum) else value


def _normal_number(value: str) -> str:
    value = value.strip()
    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        left, right = value.rsplit(",", 1)
        value = left + right if len(right) == 3 else left + "." + right
    try:
        number = float(value)
    except ValueError:
        return value
    return str(int(number)) if number.is_integer() else format(number, "g")


def _normal_unit(unit: str | None, currency: str | None) -> str | None:
    if currency:
        return _CURRENCY_CODES[currency]
    if unit is None:
        return None
    normalized = unit.casefold()
    if normalized in _PERCENT_UNITS:
        return "%"
    aliases = {
        "download": "downloads",
        "install": "installs",
        "user": "users",
        "time": "times",
        "k": "thousand",
        "m": "million",
    }
    return aliases.get(normalized, normalized)


def _numeric_tokens(text: str) -> set[tuple[str, str | None]]:
    tokens: set[tuple[str, str | None]] = set()
    for match in _NUMBER_RE.finditer(text):
        currency = match.group("currency")
        number = _normal_number(match.group("number"))
        unit = _normal_unit(match.group("unit"), currency)
        tokens.add((number, unit))
    return tokens


def _evidence_numeric_tokens(item: dict) -> set[tuple[str, str | None]]:
    evidence = item["evidence"]
    parts = [evidence.get("quote") or ""]
    value = evidence.get("value")
    unit = evidence.get("unit")
    if value is not None:
        parts.append(f"{value} {unit or ''}")
    return _numeric_tokens(" ".join(parts))


def _parse_day(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class ValidationPolicy:
    freshness_cutoff: str | date | None = None
    freshness_required: bool = False

    def __post_init__(self) -> None:
        if self.freshness_cutoff is not None and _parse_day(self.freshness_cutoff) is None:
            raise ValueError("freshness_cutoff must be an ISO date or date object")
        if self.freshness_required and self.freshness_cutoff is None:
            raise ValueError("freshness_cutoff is required when freshness_required is true")


@dataclass(frozen=True)
class ValidationReport:
    run_id: str
    status: RunStatus | str
    confidence: ConfidenceLevel | str
    claims: tuple[Claim, ...]
    issues: tuple[ResearchIssue, ...]
    stop_reason: str


class Validator:
    """Deterministic grounding, freshness and run-status checks for one run."""

    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    def validate_run(
        self,
        run_id: str,
        policy: ValidationPolicy | None = None,
        *,
        finalize: bool = True,
        persist: bool = True,
        stop_reason_override: StopReason | str | None = None,
    ) -> ValidationReport:
        run = self.repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Research run not found: {run_id}")
        contract = self.repository.get_research_contract(run_id)
        if policy is None:
            contract_cutoff = contract.get("freshness_cutoff") if contract else None
            policy = ValidationPolicy(
                freshness_cutoff=contract_cutoff,
                freshness_required=contract_cutoff is not None,
            )
        effective_stop_reason = (
            _value(stop_reason_override)
            if stop_reason_override is not None
            else run.stop_reason
        )
        if finalize and persist and contract is not None:
            if not effective_stop_reason:
                raise ValueError(
                    "A contracted research run needs an explicit stop reason before finalization"
                )
            try:
                StopReason(effective_stop_reason)
            except ValueError as error:
                allowed = ", ".join(reason.value for reason in StopReason)
                raise ValueError(
                    f"Contracted run stop_reason must be one of: {allowed}"
                ) from error
        existing_issues = self.repository.list_issues(run_id)
        generated: list[ResearchIssue] = []
        validated_claims: list[Claim] = []
        freshness_by_evidence: dict[str, str] = {}

        if contract is not None:
            slot_coverage = self.repository.get_research_evidence_slot_coverage(run_id)
            for slot in slot_coverage["missing"]:
                generated.append(
                    self._issue(
                        run_id,
                        "GAP",
                        f"Required evidence slot is not covered: {slot}.",
                        severity=IssueSeverity.BLOCKING,
                        metadata={
                            "major": True,
                            "required_evidence_slot": slot,
                        },
                    )
                )

        for claim in self.repository.list_claims(run_id):
            trace = self.repository.get_claim_trace(claim.id)
            evidence_items = trace["evidence"] if trace else []
            claim_issue_types: set[str] = set()
            freshness_findings: set[str] = set()

            support_items = [
                item for item in evidence_items if item["relation"] == "SUPPORTS"
            ]
            claim_metric = normalize_metric(claim.target_metric)
            metric_support_items = [
                item
                for item in support_items
                if normalize_metric(item["evidence"].get("metric")) is not None
            ]
            untyped_support_items = [
                item
                for item in support_items
                if normalize_metric(item["evidence"].get("metric")) is None
            ]
            claim_type = _value(claim.claim_type)
            if (
                claim_metric is None
                and metric_support_items
                and claim_type in {"FACT", "ESTIMATE", "INFERENCE"}
            ):
                first_support = min(
                    metric_support_items,
                    key=lambda item: item["evidence"]["id"],
                )
                evidence_id = first_support["evidence"]["id"]
                generated.append(
                    self._issue(
                        run_id,
                        "CLAIM_METRIC_UNSPECIFIED",
                        "Claim target_metric is required when supporting evidence declares a metric.",
                        severity=IssueSeverity.BLOCKING,
                        related_claim_id=claim.id,
                        related_evidence_id=evidence_id,
                        metadata={
                            "evidence_metric": normalize_metric(
                                first_support["evidence"].get("metric")
                            )
                        },
                    )
                )
                claim_issue_types.add("CLAIM_METRIC_UNSPECIFIED")
            elif claim_metric is not None:
                mismatched_supports = [
                    item
                    for item in metric_support_items
                    if normalize_metric(item["evidence"].get("metric")) != claim_metric
                ]
                for item in mismatched_supports:
                    evidence_metric = normalize_metric(item["evidence"].get("metric"))
                    generated.append(
                        self._issue(
                            run_id,
                            "METRIC_SUPPORT_MISMATCH",
                            f"Supporting evidence metric '{evidence_metric}' does not match claim target_metric '{claim_metric}'.",
                            severity=IssueSeverity.BLOCKING,
                            related_claim_id=claim.id,
                            related_evidence_id=item["evidence"]["id"],
                            metadata={
                                "target_metric": claim_metric,
                                "evidence_metric": evidence_metric,
                            },
                        )
                    )
                if not metric_support_items and untyped_support_items:
                    for item in untyped_support_items:
                        generated.append(
                            self._issue(
                                run_id,
                                "METRIC_SUPPORT_UNKNOWN",
                                "Supporting evidence has no metric and cannot support the claim target_metric.",
                                severity=IssueSeverity.BLOCKING,
                                related_claim_id=claim.id,
                                related_evidence_id=item["evidence"]["id"],
                                metadata={"target_metric": claim_metric},
                            )
                        )
                    claim_issue_types.add("METRIC_SUPPORT_UNKNOWN")
                if mismatched_supports:
                    claim_issue_types.add("METRIC_SUPPORT_MISMATCH")
            directional_items = [
                item
                for item in support_items
                if self._evidence_direction(item["evidence"]) in {"UP", "DOWN"}
            ]
            for index, first in enumerate(directional_items):
                for second in directional_items[index + 1 :]:
                    first_evidence = first["evidence"]
                    second_evidence = second["evidence"]
                    comparison = compare_evidence(first_evidence, second_evidence)
                    evidence_ids = sorted(
                        {first_evidence["id"], second_evidence["id"]}
                    )
                    first_direction = self._evidence_direction(first_evidence)
                    second_direction = self._evidence_direction(second_evidence)
                    shared_metadata = {
                        "evidence_ids": evidence_ids,
                        "directions": {
                            first_evidence["id"]: first_direction,
                            second_evidence["id"]: second_direction,
                        },
                    }
                    if not comparison.comparable:
                        generated.append(
                            self._issue(
                                run_id,
                                "NOT_COMPARABLE",
                                "Directional evidence cannot be compared directly: "
                                + ", ".join(comparison.reasons)
                                + f" ({evidence_ids[0]} vs {evidence_ids[1]}).",
                                severity=IssueSeverity.WARNING,
                                related_claim_id=claim.id,
                                related_evidence_id=evidence_ids[0],
                                source_id=first["source"]["id"],
                                metadata={
                                    **shared_metadata,
                                    "comparability": "NOT_COMPARABLE",
                                    "reasons": list(comparison.reasons),
                                },
                            )
                        )
                    elif {first_direction, second_direction} == {"UP", "DOWN"}:
                        generated.append(
                            self._issue(
                                run_id,
                                "CONFLICT",
                                "Comparable evidence reports opposite directions "
                                + f"({evidence_ids[0]} vs {evidence_ids[1]}).",
                                severity=IssueSeverity.ERROR,
                                related_claim_id=claim.id,
                                related_evidence_id=evidence_ids[0],
                                source_id=first["source"]["id"],
                                metadata={
                                    **shared_metadata,
                                    "comparability": "COMPARABLE",
                                    "signature": comparison.signature,
                                },
                            )
                        )

            lineage_audit = self.repository.get_claim_lineage_audit(claim.id)
            support_evidence_ids = {
                item["evidence"]["id"] for item in support_items
            }
            for root in (lineage_audit or {}).get("root_sources", []):
                root_support_ids = set(root["supporting_evidence_ids"])
                source_ids = sorted(
                    {
                        edge["source_id"]
                        for edge in (lineage_audit or {}).get("edges", [])
                        if edge["root_source_id"] == root["root_source_id"]
                        and edge["evidence_id"] in support_evidence_ids
                    }
                )
                if len(source_ids) > 1 and root_support_ids:
                    generated.append(
                        self._issue(
                            run_id,
                            "SHARED_ORIGIN",
                            "Multiple supporting documents trace to the same root source.",
                            severity=IssueSeverity.INFO,
                            related_claim_id=claim.id,
                            related_evidence_id=sorted(root_support_ids)[0],
                            source_id=source_ids[0],
                            metadata={
                                "root_source_id": root["root_source_id"],
                                "source_ids": source_ids,
                                "evidence_ids": sorted(root_support_ids),
                            },
                        )
                    )

            if not evidence_items:
                generated.append(
                    self._issue(
                        run_id,
                        "MISSING_EVIDENCE",
                        "Claim has no linked evidence.",
                        severity=IssueSeverity.BLOCKING,
                        related_claim_id=claim.id,
                    )
                )
                claim_issue_types.add("MISSING_EVIDENCE")

            claim_tokens = _numeric_tokens(claim.text)
            evidence_tokens: set[tuple[str, str | None]] = set()
            for item in evidence_items:
                evidence_tokens.update(_evidence_numeric_tokens(item))
                finding = self._freshness_finding(item, policy)
                if finding:
                    evidence_id = item["evidence"]["id"]
                    freshness_by_evidence[evidence_id] = finding
                    freshness_findings.add(finding)
                    self._record_freshness_issue(generated, run_id, item, finding)

            unsupported = sorted(claim_tokens - evidence_tokens)
            if unsupported:
                tokens_text = ", ".join(
                    f"{number}{unit or ''}" for number, unit in unsupported
                )
                generated.append(
                    self._issue(
                        run_id,
                        "UNSUPPORTED_NUMERIC_ASSERTION",
                        f"Numeric token(s) are not grounded by linked evidence: {tokens_text}.",
                        severity=IssueSeverity.BLOCKING,
                        related_claim_id=claim.id,
                    )
                )
                claim_issue_types.add("UNSUPPORTED_NUMERIC_ASSERTION")

            valid = not claim_issue_types
            status = ClaimStatus.VALID if valid else ClaimStatus.INVALID
            linked_evidence_ids = {item["evidence"]["id"] for item in evidence_items}
            manual_claim_issues = [
                issue
                for issue in existing_issues
                if issue.status == IssueStatus.OPEN
                and issue.metadata.get("origin") != "validator"
                and (
                    issue.related_claim_id == claim.id
                    or issue.evidence_id in linked_evidence_ids
                    or bool(
                        set(issue.metadata.get("evidence_ids", []))
                        & linked_evidence_ids
                    )
                )
            ]
            current_claim_issues = manual_claim_issues + [
                issue
                for issue in generated
                if issue.related_claim_id == claim.id
            ]
            has_conflict = any(
                issue.code == "CONFLICT" and issue.status == IssueStatus.OPEN
                for issue in current_claim_issues
            )
            has_not_comparable = any(
                issue.code == "NOT_COMPARABLE" and issue.status == IssueStatus.OPEN
                for issue in current_claim_issues
            )
            has_blocking_gap = any(
                issue.code == "GAP"
                and issue.status == IssueStatus.OPEN
                and (
                    issue.severity in {IssueSeverity.BLOCKING, IssueSeverity.ERROR}
                    or issue.metadata.get("major") is True
                )
                for issue in current_claim_issues
            )
            audit = lineage_audit or {
                "supporting_independent_root_count": 0,
            }
            confidence = claim_confidence(
                is_valid=valid,
                freshness_findings=freshness_findings,
                is_current=(
                    policy.freshness_cutoff is not None and not freshness_findings
                ),
                independent_root_count=audit["supporting_independent_root_count"],
                has_unresolved_conflict=has_conflict,
                has_relevant_not_comparable=has_not_comparable,
                has_blocking_gap=has_blocking_gap,
            )
            rationale = self._claim_rationale(valid, freshness_findings, confidence)
            if persist:
                self.repository.update_claim_validation(
                    claim.id, status, confidence, rationale
                )
            validated_claims.append(
                replace(
                    claim,
                    status=status,
                    confidence_level=confidence,
                    confidence_rationale=rationale,
                )
            )

        current_ids = {issue.id for issue in generated}
        if persist:
            for old_issue in existing_issues:
                if (
                    old_issue.metadata.get("origin") == "validator"
                    and old_issue.status == IssueStatus.OPEN
                    and old_issue.id not in current_ids
                ):
                    self.repository.update_issue_status(old_issue.id, IssueStatus.RESOLVED)
            for issue in generated:
                self.repository.save_issue(issue)

        manual_open = [
            issue
            for issue in existing_issues
            if issue.metadata.get("origin") != "validator" and issue.status == IssueStatus.OPEN
        ]
        generated_open = [issue for issue in generated if issue.status == IssueStatus.OPEN]
        active_issues = manual_open + generated_open
        valid_claims = [claim for claim in validated_claims if claim.status == ClaimStatus.VALID]

        if not finalize:
            status = RunStatus.ACTIVE
            validation_reason = "Research run remains active; validation findings are provisional."
        else:
            status, validation_reason = self._run_status(valid_claims, active_issues)

        if contract is not None:
            report_stop_reason = effective_stop_reason if finalize else validation_reason
            persisted_stop_reason = run.stop_reason
        else:
            report_stop_reason = validation_reason
            persisted_stop_reason = validation_reason

        confidence = run_confidence(status, [claim.confidence_level for claim in validated_claims])
        if persist:
            self.repository.update_run_validation(
                run_id,
                status,
                datetime.now(timezone.utc).isoformat() if finalize else None,
                persisted_stop_reason,
            )
        persisted_issues = (
            tuple(self.repository.list_issues(run_id))
            if persist
            else tuple(active_issues)
        )
        return ValidationReport(
            run_id=run_id,
            status=status,
            confidence=confidence,
            claims=tuple(validated_claims),
            issues=persisted_issues,
            stop_reason=report_stop_reason or "",
        )

    def _freshness_finding(
        self, item: dict, policy: ValidationPolicy
    ) -> str | None:
        if policy.freshness_cutoff is None:
            return None
        evidence = item["evidence"]
        source = item["source"]
        cutoff = _parse_day(policy.freshness_cutoff)
        published_at = _parse_day(source.get("published_at"))
        observed_at = _parse_day(evidence.get("observed_at") or evidence.get("period_end"))
        if cutoff is not None and any(
            value is not None and value < cutoff
            for value in (published_at, observed_at)
        ):
            return "STALE_EVIDENCE"
        # Source publication and metric observation are separate clocks. A
        # recent observation cannot establish when an undated source appeared.
        if published_at is None or observed_at is None:
            return "FRESHNESS_UNKNOWN"
        return None

    def _record_freshness_issue(
        self,
        issues: list[ResearchIssue],
        run_id: str,
        item: dict,
        finding: str,
    ) -> None:
        evidence = item["evidence"]
        source = item["source"]
        message = (
            "The source publication date or metric observation period predates the explicit freshness cutoff."
            if finding == "STALE_EVIDENCE"
            else "Freshness was required, but the source publication date or metric observation period is unknown."
        )
        issues.append(
            self._issue(
                run_id,
                finding,
                message,
                severity=IssueSeverity.WARNING,
                related_evidence_id=evidence["id"],
                source_id=source["id"],
            )
        )

    @staticmethod
    def _claim_rationale(
        valid: bool,
        freshness_findings: set[str],
        confidence: ConfidenceLevel,
    ) -> str:
        if not valid:
            return "Claim is invalid because required evidence linkage or numeric grounding is missing."
        if "STALE_EVIDENCE" in freshness_findings:
            return "Evidence is linked, but at least one item predates the run's freshness cutoff."
        if "FRESHNESS_UNKNOWN" in freshness_findings:
            return "Evidence is linked, but freshness could not be established from dated source data."
        if confidence == ConfidenceLevel.STRONG:
            return "Claim is valid, current and supported by at least two independent roots without a blocking integrity issue."
        if confidence == ConfidenceLevel.WEAK:
            return "Claim is valid, but unresolved comparable contradictory evidence caps confidence at WEAK."
        return "Claim is valid, but it does not meet every STRONG confidence requirement."

    @staticmethod
    def _issue(
        run_id: str,
        code: str,
        message: str,
        *,
        severity: IssueSeverity,
        related_claim_id: str | None = None,
        related_evidence_id: str | None = None,
        source_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ResearchIssue:
        stable_key = ":".join(
            (
                run_id,
                code,
                related_claim_id or "",
                related_evidence_id or "",
                message,
            )
        )
        return ResearchIssue(
            id=str(uuid5(NAMESPACE_URL, f"gamota-validator:{stable_key}")),
            run_id=run_id,
            code=code,
            message=message,
            severity=severity,
            status=IssueStatus.OPEN,
            related_claim_id=related_claim_id,
            evidence_id=related_evidence_id,
            source_id=source_id,
            metadata={"origin": "validator", **(metadata or {})},
        )

    @staticmethod
    def _evidence_direction(evidence: dict) -> str | None:
        metadata = evidence.get("metadata") or {}
        direction = metadata.get("direction")
        if direction is None:
            return None
        normalized = str(direction).strip().upper()
        return normalized if normalized in {"UP", "DOWN", "FLAT"} else None

    @staticmethod
    def _run_status(
        valid_claims: list[Claim], issues: list[ResearchIssue]
    ) -> tuple[RunStatus, str]:
        fatal = next(
            (
                issue
                for issue in issues
                if issue.code == "INFRASTRUCTURE_FAILURE"
                or issue.metadata.get("fatal") is True
            ),
            None,
        )
        if fatal:
            return RunStatus.FAILED, f"Fatal infrastructure issue: {fatal.code}."

        ambiguity = next(
            (
                issue
                for issue in issues
                if issue.code == "AMBIGUITY"
                and issue.severity in {IssueSeverity.BLOCKING, IssueSeverity.ERROR}
            ),
            None,
        )
        if ambiguity:
            return RunStatus.NEEDS_CLARIFICATION, "Blocking ambiguity requires a clarified question."

        if not valid_claims:
            return RunStatus.INSUFFICIENT_DATA, "No validated claims are supported by linked evidence."

        blocker = next(
            (
                issue
                for issue in issues
                if issue.severity in {IssueSeverity.BLOCKING, IssueSeverity.ERROR}
                or (issue.code == "GAP" and issue.metadata.get("major") is True)
            ),
            None,
        )
        if blocker:
            return RunStatus.PARTIAL, f"Run has an unresolved blocking issue: {blocker.code}."
        return RunStatus.COMPLETE, "Validation completed without blocking issues."
