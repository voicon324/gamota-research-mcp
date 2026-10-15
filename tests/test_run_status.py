from __future__ import annotations

from gamota_research.models import ResearchIssue
from gamota_research.validator import Validator


def _add_valid_claim(repository, run_id: str):
    source = repository.save_source(
        run_id=run_id,
        url="https://example.test/signal",
        title="Fixture signal",
        source_type="REPORT",
    )
    evidence = repository.save_evidence(
        run_id=run_id,
        source_id=source.id,
        quote="Fixture: a qualitative signal was observed.",
        locator="section 1",
        source_mode="FIXTURE",
    )
    claim = repository.save_claim(run_id=run_id, text="A signal was observed.", claim_type="FACT")
    repository.link_claim_evidence(claim.id, evidence.id)
    return claim


def test_blocking_ambiguity_requires_clarification(repository):
    run = repository.create_run("Which genre is best?")
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="AMBIGUITY",
            message="The decision criterion is unspecified.",
            severity="BLOCKING",
        )
    )

    result = Validator(repository).validate_run(run.id)

    assert result.status == "NEEDS_CLARIFICATION"


def test_valid_claim_with_blocking_gap_is_partial(repository):
    run = repository.create_run("Assess a bounded signal")
    _add_valid_claim(repository, run.id)
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="GAP",
            message="No comparable genre-level revenue evidence.",
            severity="BLOCKING",
        )
    )

    result = Validator(repository).validate_run(run.id)

    assert result.status == "PARTIAL"


def test_infrastructure_failure_sets_failed_status(repository):
    run = repository.create_run("A run with an infrastructure failure")
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="INFRASTRUCTURE_FAILURE",
            message="The persistence layer failed.",
            severity="ERROR",
        )
    )

    result = Validator(repository).validate_run(run.id)

    assert result.status == "FAILED"
