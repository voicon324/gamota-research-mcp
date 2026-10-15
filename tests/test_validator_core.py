from __future__ import annotations

import pytest


def _load_validator():
    try:
        from gamota_research.validator import Validator
    except ModuleNotFoundError as error:
        pytest.fail(f"validator is not implemented yet: {error}")
    return Validator


def test_fact_claim_without_evidence_is_retained_but_blocked(repository):
    Validator = _load_validator()
    run = repository.create_run("What is the observed market signal?")
    claim = repository.save_claim(
        run_id=run.id,
        text="A factual claim with no attached source.",
        claim_type="FACT",
    )

    result = Validator(repository).validate_run(run.id)

    assert result.status == "INSUFFICIENT_DATA"
    assert any(
        issue.code == "MISSING_EVIDENCE"
        and issue.severity == "BLOCKING"
        and issue.related_claim_id == claim.id
        for issue in result.issues
    )
    stored_claim = next(item for item in repository.list_claims(run.id) if item.id == claim.id)
    assert stored_claim.status == "INVALID"
    assert stored_claim.confidence_level == "INSUFFICIENT"


def test_validator_persists_issues_for_later_readback(repository):
    Validator = _load_validator()
    run = repository.create_run("Keep validation findings auditable")
    repository.save_claim(run_id=run.id, text="Unbacked fact", claim_type="FACT")

    result = Validator(repository).validate_run(run.id)
    stored_issues = repository.list_issues(run.id)

    assert any(issue.code == "MISSING_EVIDENCE" for issue in result.issues)
    assert any(issue.code == "MISSING_EVIDENCE" for issue in stored_issues)
