from __future__ import annotations

from gamota_research.validator import ValidationPolicy, Validator


def _claim_with_pair(
    repository,
    *,
    first_metric,
    first_direction,
    second_metric,
    second_direction,
    target_metric,
):
    run = repository.create_run("Compare two directional evidence items")
    evidence_items = []
    for index, (metric, direction) in enumerate(
        [
            (first_metric, first_direction),
            (second_metric, second_direction),
        ],
        start=1,
    ):
        source = repository.save_source(
            run_id=run.id,
            url=f"https://example.test/source-{index}",
            title=f"Fixture source {index}",
            source_type="REPORT",
        )
        evidence_items.append(
            repository.save_evidence(
                run_id=run.id,
                source_id=source.id,
                quote=f"Fixture direction {direction}.",
                locator="section 1",
                metric=metric,
                unit="%",
                market="VN",
                period_start="2025-01-01",
                period_end="2025-06-30",
                observed_at="2025-05-02",
                source_mode="FIXTURE",
                metadata={"direction": direction},
            )
        )
    claim = repository.save_claim(
        run_id=run.id,
        text="A qualitative market signal was reported.",
        claim_type="INFERENCE",
        target_metric=target_metric,
    )
    for evidence in evidence_items:
        repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")
    return run, claim, evidence_items


def test_comparable_up_down_evidence_creates_persisted_conflict(repository):
    run, claim, evidence = _claim_with_pair(
        repository,
        first_metric="revenue_growth",
        first_direction="UP",
        second_metric="revenue_growth",
        second_direction="DOWN",
        target_metric="revenue_growth",
    )

    report = Validator(repository).validate_run(run.id)

    conflict = next(issue for issue in report.issues if issue.code == "CONFLICT")
    assert conflict.related_claim_id == claim.id
    assert set(conflict.metadata["evidence_ids"]) == {item.id for item in evidence}
    assert conflict.metadata["comparability"] == "COMPARABLE"
    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.confidence_level == "WEAK"


def test_non_comparable_directions_are_reported_without_false_conflict(repository):
    run, claim, evidence = _claim_with_pair(
        repository,
        first_metric="revenue_growth",
        first_direction="UP",
        second_metric="downloads_growth",
        second_direction="DOWN",
        target_metric="revenue_growth",
    )

    report = Validator(repository).validate_run(
        run.id,
        ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True),
    )

    non_comparable = next(
        issue for issue in report.issues if issue.code == "NOT_COMPARABLE"
    )
    assert non_comparable.related_claim_id == claim.id
    assert set(non_comparable.metadata["evidence_ids"]) == {item.id for item in evidence}
    assert not any(issue.code == "CONFLICT" for issue in report.issues)
    mismatch = next(
        issue
        for issue in report.issues
        if issue.code == "METRIC_SUPPORT_MISMATCH"
        and issue.related_claim_id == claim.id
    )
    assert mismatch.evidence_id == evidence[1].id
    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == "INVALID"
    assert checked.confidence_level == "INSUFFICIENT"
