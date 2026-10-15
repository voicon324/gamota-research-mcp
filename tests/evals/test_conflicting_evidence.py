from __future__ import annotations

from gamota_research.validator import Validator

from .helpers import add_claim, add_evidence


def test_opposite_comparable_signals_produce_conflict_and_cap_confidence(repository):
    run = repository.create_run("Does the same market metric move up or down?")
    evidence = []
    for index, direction in enumerate(("UP", "DOWN"), start=1):
        _, item = add_evidence(
            repository,
            run.id,
            url=f"https://example.test/metric-{index}",
            quote=f"FIXTURE: the metric moved {direction.lower()}.",
            metric="revenue_growth",
            unit="%",
            market="VN",
            period_start="2025-01-01",
            period_end="2025-12-31",
            scope="same mobile game sample",
            method="same measurement basis",
            direction=direction,
        )
        evidence.append(item)
    claim = add_claim(
        repository,
        run.id,
        text="FIXTURE: the segment has a clear upward signal.",
        target_metric="revenue_growth",
        evidence_relations=[(item, "SUPPORTS") for item in evidence],
    )

    report = Validator(repository).validate_run(run.id)

    conflict = next(
        item for item in report.issues if item.code == "CONFLICT"
    )
    checked = next(item for item in report.claims if item.id == claim.id)
    assert conflict.metadata["comparability"] == "COMPARABLE"
    assert set(conflict.metadata["evidence_ids"]) == {item.id for item in evidence}
    assert checked.status == "VALID"
    assert checked.confidence_level == "WEAK"
    assert report.status == "PARTIAL"
