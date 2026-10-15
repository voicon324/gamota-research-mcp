from __future__ import annotations

from typing import Any

from .contract import ResearchContract
from .enums import EvidenceRelation, StopReason
from .models import ClaimEvidence, ResearchIssue, ResearchRun
from .repository import ResearchRepository


class ResearchService:
    """Thin application layer for MCP tools added in a later slice."""

    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    def create_run(self, question: str) -> ResearchRun:
        return self.repository.create_run(question)

    def get_run(self, run_id: str) -> ResearchRun | None:
        return self.repository.get_run(run_id)

    def set_research_contract(
        self, run_id: str, contract: ResearchContract | dict[str, Any]
    ) -> dict[str, Any]:
        return self.repository.set_research_contract(run_id, contract)

    def get_research_contract(self, run_id: str) -> dict[str, Any] | None:
        return self.repository.get_research_contract(run_id)

    def update_research_progress(self, run_id: str, **counts: int | None) -> dict[str, int]:
        return self.repository.update_research_progress(run_id, **counts)

    def get_research_budget_status(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_research_budget_status(run_id)

    def consume_domain_tool_budget(self, run_id: str) -> dict[str, int]:
        return self.repository.consume_domain_tool_budget(run_id)

    def get_research_evidence_slot_coverage(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_research_evidence_slot_coverage(run_id)

    def set_stop_reason(self, run_id: str, stop_reason: StopReason | str) -> None:
        try:
            normalized = StopReason(stop_reason)
        except ValueError as error:
            allowed = ", ".join(reason.value for reason in StopReason)
            raise ValueError(f"stop_reason must be one of: {allowed}") from error
        self.repository.set_run_stop_reason(run_id, normalized.value)

    def save_source(self, **fields: Any):
        return self.repository.save_source(**fields)

    def save_evidence(self, **fields: Any):
        return self.repository.save_evidence(**fields)

    def save_claim(self, **fields: Any):
        return self.repository.save_claim(**fields)

    def link_claim_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        relation: EvidenceRelation | str = EvidenceRelation.SUPPORTS,
    ) -> ClaimEvidence:
        return self.repository.link_claim_evidence(claim_id, evidence_id, relation)

    def save_issue(self, issue: ResearchIssue | None = None, **fields: Any) -> ResearchIssue:
        return self.repository.save_issue(issue, **fields)

    def trace_claim(self, claim_id: str) -> dict[str, Any] | None:
        return self.repository.get_claim_trace(claim_id)

    def get_claim_lineage_audit(self, claim_id: str) -> dict[str, Any] | None:
        return self.repository.get_claim_lineage_audit(claim_id)
