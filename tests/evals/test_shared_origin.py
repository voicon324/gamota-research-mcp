from __future__ import annotations

from gamota_research.validator import ValidationPolicy, Validator

from .helpers import add_claim, add_evidence


def test_three_articles_citing_one_report_count_as_one_independent_root(repository):
    run = repository.create_run("Count independent sources behind repeated coverage")
    root = repository.save_source(
        run_id=run.id,
        url="https://example.test/original-report",
        title="Fixture original report",
        source_type="REPORT",
        published_at="2026-02-01",
    )
    evidence = []
    for index in range(1, 4):
        _, item = add_evidence(
            repository,
            run.id,
            url=f"https://example.test/article-{index}",
            parent_source_id=root.id,
            source_type="NEWS",
            quote=f"FIXTURE article {index}: cites the same original report.",
            metric="revenue_growth",
            unit="%",
            market="VN",
            period_start="2025-01-01",
            period_end="2025-12-31",
            scope="same reported market",
            method="secondary article quoting report",
        )
        evidence.append(item)
    claim = add_claim(
        repository,
        run.id,
        text="FIXTURE: several articles describe market growth.",
        target_metric="revenue_growth",
        evidence_relations=[(item, "SUPPORTS") for item in evidence],
    )

    report = Validator(repository).validate_run(
        run.id,
        ValidationPolicy(freshness_cutoff="2026-01-01", freshness_required=True),
    )
    audit = repository.get_claim_lineage_audit(claim.id)
    shared = next(item for item in report.issues if item.code == "SHARED_ORIGIN")
    checked = next(item for item in report.claims if item.id == claim.id)

    assert audit["document_count"] == 3
    assert audit["independent_root_count"] == 1
    assert audit["supporting_independent_root_count"] == 1
    assert shared.metadata["root_source_id"] == root.id
    assert len(shared.metadata["source_ids"]) == 3
    assert checked.confidence_level == "MODERATE"
    assert checked.confidence_level != "STRONG"
