from __future__ import annotations


def test_claim_lineage_audit_counts_documents_roots_and_edges(repository):
    run = repository.create_run("Audit independent evidence roots")
    report = repository.save_source(
        run_id=run.id,
        url="https://example.test/report",
        title="Original report",
        source_type="REPORT",
    )
    article_a = repository.save_source(
        run_id=run.id,
        url="https://example.test/article-a",
        title="Article A",
        source_type="NEWS",
        parent_source_id=report.id,
    )
    article_b = repository.save_source(
        run_id=run.id,
        url="https://example.test/article-b",
        title="Article B",
        source_type="NEWS",
        parent_source_id=report.id,
    )
    store_snapshot = repository.save_source(
        run_id=run.id,
        url="https://example.test/store",
        title="Store snapshot",
        source_type="STORE_LISTING",
    )
    sources = [article_a, article_b, store_snapshot]
    evidence = [
        repository.save_evidence(
            run_id=run.id,
            source_id=source.id,
            quote=f"Evidence from {source.title}.",
            locator="section 1",
            source_mode="FIXTURE",
        )
        for source in sources
    ]
    claim = repository.save_claim(
        run_id=run.id,
        text="A traceable research finding.",
        claim_type="INFERENCE",
    )
    for item in evidence:
        repository.link_claim_evidence(claim.id, item.id, "SUPPORTS")

    audit = repository.get_claim_lineage_audit(claim.id)
    from gamota_research.service import ResearchService

    assert ResearchService(repository).get_claim_lineage_audit(claim.id) == audit

    assert audit["claim"]["id"] == claim.id
    assert audit["evidence_count"] == 3
    assert audit["document_count"] == 3
    assert audit["independent_root_count"] == 2
    assert {edge["evidence_id"] for edge in audit["edges"]} == {
        item.id for item in evidence
    }
    assert {edge["root_source_id"] for edge in audit["edges"]} == {
        report.id,
        store_snapshot.id,
    }
    report_lineage = next(
        root for root in audit["root_sources"] if root["root_source_id"] == report.id
    )
    assert set(report_lineage["supporting_evidence_ids"]) == {
        evidence[0].id,
        evidence[1].id,
    }
    assert set(report_lineage["descendant_source_ids"]) == {
        report.id,
        article_a.id,
        article_b.id,
    }


def test_shared_origin_is_reported_without_discarding_evidence(repository):
    from gamota_research.validator import ValidationPolicy, Validator

    run = repository.create_run("Detect repeated reporting of one root source")
    root = repository.save_source(
        run_id=run.id,
        url="https://example.test/original-report",
        title="Original report",
        source_type="REPORT",
        published_at="2025-05-01",
    )
    claim = repository.save_claim(
        run_id=run.id,
        text="A repeated qualitative signal.",
        claim_type="INFERENCE",
    )
    for index in range(3):
        article = repository.save_source(
            run_id=run.id,
            url=f"https://example.test/article-{index}",
            title=f"Article {index}",
            source_type="NEWS",
            parent_source_id=root.id,
            published_at="2025-05-01",
        )
        evidence = repository.save_evidence(
            run_id=run.id,
            source_id=article.id,
            quote=f"Fixture report {index} cites the same original report.",
            locator="paragraph 1",
            observed_at="2025-05-02",
            source_mode="FIXTURE",
        )
        repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")

    report = Validator(repository).validate_run(
        run.id,
        ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True),
    )

    shared = next(issue for issue in report.issues if issue.code == "SHARED_ORIGIN")
    assert shared.related_claim_id == claim.id
    assert shared.metadata["root_source_id"] == root.id
    assert len(shared.metadata["source_ids"]) == 3
    audit = repository.get_claim_lineage_audit(claim.id)
    assert audit["evidence_count"] == 3
    assert audit["document_count"] == 3
    assert audit["independent_root_count"] == 1
    assert audit["supporting_independent_root_count"] == 1
    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == "VALID"
    assert checked.confidence_level == "MODERATE"
