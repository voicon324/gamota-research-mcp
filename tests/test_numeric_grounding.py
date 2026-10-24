from __future__ import annotations

from gamota_research.validator import Validator


def _grounded_claim(repository, claim_text: str, quote: str, value=18, unit="%", metadata=None):
    run = repository.create_run("Check numeric claim grounding")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/metric",
        title="Fixture metric source",
        source_type="REPORT",
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote=quote,
        locator="table 1",
        metric="growth",
        value=value,
        unit=unit,
        source_mode="FIXTURE",
        metadata=metadata or {},
    )
    claim = repository.save_claim(
        run_id=run.id,
        text=claim_text,
        claim_type="FACT",
        target_metric="growth",
    )
    repository.link_claim_evidence(claim.id, evidence.id)
    return run, claim


def test_numeric_claim_matching_evidence_passes(repository):
    run, claim = _grounded_claim(
        repository,
        "Genre X increased by 18%.",
        "Fixture: installs increased by 18%.",
    )

    result = Validator(repository).validate_run(run.id)

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "VALID"
    assert not any(issue.code == "UNSUPPORTED_NUMERIC_ASSERTION" for issue in result.issues)


def test_numeric_claim_mismatch_is_rejected(repository):
    run, claim = _grounded_claim(
        repository,
        "Genre X increased by 25%.",
        "Fixture: installs increased by 18%.",
    )

    result = Validator(repository).validate_run(run.id)

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "INVALID"
    assert stored_claim.confidence_level == "INSUFFICIENT"
    assert result.status == "INSUFFICIENT_DATA"
    assert any(issue.code == "UNSUPPORTED_NUMERIC_ASSERTION" for issue in result.issues)


def test_percent_claim_is_not_grounded_by_unitless_evidence(repository):
    run, claim = _grounded_claim(
        repository,
        "Genre X increased by 18%.",
        "Fixture: installs increased by 18.",
        unit=None,
    )

    result = Validator(repository).validate_run(run.id)

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "INVALID"
    assert any(issue.code == "UNSUPPORTED_NUMERIC_ASSERTION" for issue in result.issues)


def test_unitless_claim_is_not_grounded_by_percent_evidence(repository):
    run, claim = _grounded_claim(
        repository,
        "Genre X increased by 18.",
        "Fixture: installs increased by 18%.",
        unit="%",
    )

    result = Validator(repository).validate_run(run.id)

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "INVALID"
    assert any(issue.code == "UNSUPPORTED_NUMERIC_ASSERTION" for issue in result.issues)


def test_numeric_value_in_arbitrary_metadata_does_not_ground_claim(repository):
    run, claim = _grounded_claim(
        repository,
        "Genre X increased by 18%.",
        "The source describes growth but does not state the amount.",
        value=None,
        unit=None,
        metadata={"internal_note": "18%"},
    )

    result = Validator(repository).validate_run(run.id)

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "INVALID"
    assert any(issue.code == "UNSUPPORTED_NUMERIC_ASSERTION" for issue in result.issues)
