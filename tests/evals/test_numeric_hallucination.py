from __future__ import annotations

from gamota_research.validator import Validator

from .helpers import add_claim, add_evidence


def test_claim_percentage_not_present_in_linked_evidence_is_rejected(repository):
    run = repository.create_run("Check a reported numeric growth claim")
    _, evidence = add_evidence(
        repository,
        run.id,
        url="https://example.test/growth-report",
        quote="FIXTURE: downloads grew by 18% year over year.",
        metric="downloads_growth",
        value=18,
        unit="%",
        market="VN",
        period_start="2025-01-01",
        period_end="2025-12-31",
    )
    claim = add_claim(
        repository,
        run.id,
        text="FIXTURE: downloads grew by 25% year over year.",
        target_metric="downloads_growth",
        evidence_relations=[(evidence, "SUPPORTS")],
    )

    report = Validator(repository).validate_run(run.id)

    unsupported = next(
        item
        for item in report.issues
        if item.code == "UNSUPPORTED_NUMERIC_ASSERTION"
        and item.related_claim_id == claim.id
    )
    checked = next(item for item in report.claims if item.id == claim.id)
    assert "25%" in unsupported.message
    assert checked.status == "INVALID"
    assert checked.confidence_level == "INSUFFICIENT"
    assert report.status == "INSUFFICIENT_DATA"
