from __future__ import annotations

from gamota_research.validator import ValidationPolicy, Validator


def _claim_with_source_date(repository, source_date: str | None, *, observed_at=None):
    run = repository.create_run("Check evidence freshness")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/freshness",
        title="Fixture source",
        source_type="REPORT",
        published_at=source_date,
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="Fixture evidence without numeric claims.",
        locator="paragraph 1",
        observed_at=observed_at,
        source_mode="FIXTURE",
    )
    claim = repository.save_claim(run_id=run.id, text="A qualitative signal.", claim_type="FACT")
    repository.link_claim_evidence(claim.id, evidence.id)
    return run, claim


def test_evidence_before_explicit_cutoff_is_stale_and_lowers_confidence(repository):
    run, claim = _claim_with_source_date(repository, "2023-01-01")

    result = Validator(repository).validate_run(
        run.id, ValidationPolicy(freshness_cutoff="2025-01-01")
    )

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.status == "VALID"
    assert stored_claim.confidence_level == "WEAK"
    assert any(issue.code == "STALE_EVIDENCE" for issue in result.issues)


def test_missing_date_under_required_freshness_policy_is_unknown(repository):
    run, claim = _claim_with_source_date(repository, None)

    result = Validator(repository).validate_run(
        run.id,
        ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True),
    )

    stored_claim = next(item for item in result.claims if item.id == claim.id)
    assert stored_claim.confidence_level == "WEAK"
    assert any(issue.code == "FRESHNESS_UNKNOWN" for issue in result.issues)


def test_recent_observation_does_not_refresh_old_source_publication(repository):
    run, _ = _claim_with_source_date(
        repository, "2023-01-01", observed_at="2026-10-20"
    )

    result = Validator(repository).validate_run(
        run.id, ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True)
    )

    assert any(issue.code == "STALE_EVIDENCE" for issue in result.issues)


def test_recent_observation_does_not_replace_missing_publication_date(repository):
    run, _ = _claim_with_source_date(repository, None, observed_at="2026-10-20")

    result = Validator(repository).validate_run(
        run.id, ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True)
    )

    assert any(issue.code == "FRESHNESS_UNKNOWN" for issue in result.issues)
