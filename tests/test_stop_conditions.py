from __future__ import annotations

import pytest

from gamota_research.enums import StopReason
from gamota_research.service import ResearchService
from gamota_research.validator import Validator


def test_finalizing_a_contracted_run_requires_an_explicit_stop_reason(repository):
    run = repository.create_run("A finalized research run must explain why it stopped")
    repository.set_research_contract(
        run.id,
        {
            "question": run.question,
            "evidence_slots": ["market_evidence"],
        },
    )

    with pytest.raises(ValueError, match="explicit stop reason"):
        Validator(repository).validate_run(run.id)

    stored = repository.get_run(run.id)
    assert stored.status == "CREATED"
    assert stored.finalized_at is None


def _contracted_claim(repository, slots):
    run = repository.create_run("Check required evidence coverage")
    repository.set_research_contract(
        run.id,
        {
            "question": run.question,
            "evidence_slots": slots,
        },
    )
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/market",
        title="Fixture market source",
        source_type="REPORT",
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="Fixture: a qualitative market signal was observed.",
        locator="section 1",
        source_mode="FIXTURE",
        metadata={"evidence_slots": ["market_evidence"]},
    )
    claim = repository.save_claim(
        run_id=run.id,
        text="A qualitative market signal was observed.",
        claim_type="INFERENCE",
    )
    repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")
    ResearchService(repository).set_stop_reason(run.id, StopReason.COVERAGE_SUFFICIENT)
    return run, claim


def test_missing_required_evidence_slot_creates_blocking_gap_and_partial(repository):
    run, claim = _contracted_claim(
        repository, ["market_evidence", "store_momentum"]
    )

    report = Validator(repository).validate_run(run.id)

    gap = next(
        issue
        for issue in report.issues
        if issue.code == "GAP" and issue.metadata.get("required_evidence_slot")
    )
    assert gap.severity == "BLOCKING"
    assert gap.metadata["required_evidence_slot"] == "store_momentum"
    assert report.status == "PARTIAL"
    assert report.stop_reason == StopReason.COVERAGE_SUFFICIENT.value
    assert repository.get_run(run.id).stop_reason == StopReason.COVERAGE_SUFFICIENT.value
    assert next(item for item in report.claims if item.id == claim.id).status == "VALID"


def test_evidence_and_claim_metadata_can_cover_all_slots_without_gap(repository):
    run, claim = _contracted_claim(
        repository, ["market_evidence", "store_momentum"]
    )
    repository.save_claim(
        id=claim.id,
        run_id=run.id,
        text=claim.text,
        claim_type=claim.claim_type,
        metadata={"evidence_slots": ["store_momentum"]},
    )

    report = Validator(repository).validate_run(run.id)

    coverage = ResearchService(repository).get_research_evidence_slot_coverage(run.id)
    assert coverage["covered"] == ["market_evidence", "store_momentum"]
    assert coverage["missing"] == []
    assert coverage["complete"] is True
    assert not any(
        issue.code == "GAP" and issue.metadata.get("required_evidence_slot")
        for issue in report.issues
    )


def test_resolved_slot_gap_is_closed_on_revalidation(repository):
    run, claim = _contracted_claim(
        repository, ["market_evidence", "store_momentum"]
    )
    first = Validator(repository).validate_run(run.id)
    missing_slot_gap = next(
        issue
        for issue in first.issues
        if issue.code == "GAP" and issue.metadata.get("required_evidence_slot")
    )
    repository.save_claim(
        id=claim.id,
        run_id=run.id,
        text=claim.text,
        claim_type=claim.claim_type,
        metadata={"evidence_slots": ["store_momentum"]},
    )

    second = Validator(repository).validate_run(run.id)

    resolved = next(issue for issue in second.issues if issue.id == missing_slot_gap.id)
    assert resolved.status == "RESOLVED"
