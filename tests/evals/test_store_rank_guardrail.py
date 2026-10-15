from __future__ import annotations

from gamota_research.validator import Validator

from .helpers import add_claim, add_evidence


def test_store_rank_evidence_cannot_support_revenue_claim(repository):
    run = repository.create_run("Can store chart rank prove revenue growth?")
    _, evidence = add_evidence(
        repository,
        run.id,
        url="https://example.test/store-chart",
        quote="FIXTURE: the app appeared at rank 8 in the chart.",
        source_type="STORE_LISTING",
        metric="store_rank",
        value=8,
        unit="rank_position",
        market="VN",
        observed_at="2026-02-01",
    )
    claim = add_claim(
        repository,
        run.id,
        text="FIXTURE: the game's revenue increased.",
        target_metric="revenue",
        evidence_relations=[(evidence, "SUPPORTS")],
    )

    report = Validator(repository).validate_run(run.id)

    mismatch = next(
        item
        for item in report.issues
        if item.code == "METRIC_SUPPORT_MISMATCH"
        and item.related_claim_id == claim.id
    )
    checked = next(item for item in report.claims if item.id == claim.id)
    assert mismatch.metadata == {
        "origin": "validator",
        "target_metric": "revenue",
        "evidence_metric": "store_rank",
    }
    assert checked.status == "INVALID"
    assert checked.confidence_level == "INSUFFICIENT"
    assert report.status == "INSUFFICIENT_DATA"
