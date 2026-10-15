from __future__ import annotations

from gamota_research.validator import ValidationPolicy, Validator

from .helpers import add_claim, add_evidence


def test_stale_evidence_remains_traceable_but_cannot_receive_strong_confidence(repository):
    run = repository.create_run("Assess a trend using dated evidence")
    _, evidence = add_evidence(
        repository,
        run.id,
        url="https://example.test/old-market-report",
        quote="FIXTURE: the segment had a qualitative growth signal.",
        published_at="2023-01-01",
        observed_at=None,
    )
    claim = add_claim(
        repository,
        run.id,
        text="FIXTURE: the segment had a growth signal in the reported period.",
        target_metric=None,
        evidence_relations=[(evidence, "SUPPORTS")],
    )

    report = Validator(repository).validate_run(
        run.id, ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True)
    )

    stale = next(item for item in report.issues if item.code == "STALE_EVIDENCE")
    checked = next(item for item in report.claims if item.id == claim.id)
    assert stale.evidence_id == evidence.id
    assert checked.status == "VALID"
    assert checked.confidence_level == "WEAK"
    assert report.status == "COMPLETE"
