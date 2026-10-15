from __future__ import annotations

from gamota_research.service import ResearchService
from gamota_research.validator import ValidationPolicy, Validator


def test_good_research_completes_with_two_current_roots_and_a_trace(repository):
    service = ResearchService(repository)
    run = service.create_run("Which mobile genre signal is supported by current evidence?")

    evidence_items = []
    for slug in ("primary-report", "independent-study"):
        source = service.save_source(
            run_id=run.id,
            url=f"https://example.test/{slug}",
            title=f"Fixture {slug}",
            source_type="REPORT",
            published_at="2026-02-01",
        )
        evidence = service.save_evidence(
            run_id=run.id,
            source_id=source.id,
            quote=f"FIXTURE: the same sample reported revenue growth. ({slug})",
            locator="page 4, paragraph 2",
            observed_at="2026-02-01",
            metric="revenue_growth",
            unit="%",
            market="VN",
            period_start="2025-01-01",
            period_end="2025-12-31",
            scope="mobile games, same market and period",
            method="fixture report",
            source_mode="FIXTURE",
        )
        evidence_items.append((source, evidence))

    claim = service.save_claim(
        run_id=run.id,
        text="FIXTURE: the sampled mobile game segment had revenue growth.",
        claim_type="INFERENCE",
        target_metric="revenue_growth",
    )
    for _, evidence in evidence_items:
        service.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")

    report = Validator(repository).validate_run(
        run.id,
        ValidationPolicy(freshness_cutoff="2026-01-01", freshness_required=True),
    )
    audit = service.get_claim_lineage_audit(claim.id)
    trace = service.trace_claim(claim.id)

    checked_claim = next(item for item in report.claims if item.id == claim.id)
    assert report.status == "COMPLETE"
    assert checked_claim.status == "VALID"
    assert checked_claim.confidence_level == "STRONG"
    assert audit["independent_root_count"] == 2
    assert audit["supporting_independent_root_count"] == 2
    assert len(trace["evidence"]) == 2
    assert {item["evidence"]["locator"] for item in trace["evidence"]} == {
        "page 4, paragraph 2"
    }
    assert {item["source"]["url"] for item in trace["evidence"]} == {
        "https://example.test/primary-report",
        "https://example.test/independent-study",
    }
