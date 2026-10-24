from __future__ import annotations

from gamota_research.models import ResearchIssue
from gamota_research.validator import ValidationPolicy, Validator


def _claim_with_roots(repository, root_count: int, *, documents_per_root: int = 1):
    run = repository.create_run("Check confidence against evidence lineage")
    claim = repository.save_claim(
        run_id=run.id,
        text="A current, traceable qualitative signal.",
        claim_type="INFERENCE",
    )
    evidence_items = []
    for root_index in range(root_count):
        root = repository.save_source(
            run_id=run.id,
            url=f"https://example.test/root-{root_index}",
            title=f"Root {root_index}",
            source_type="REPORT",
            published_at="2025-05-01",
        )
        for document_index in range(documents_per_root):
            source = root
            if document_index:
                source = repository.save_source(
                    run_id=run.id,
                    url=f"https://example.test/root-{root_index}/article-{document_index}",
                    title=f"Article {root_index}-{document_index}",
                    source_type="NEWS",
                    published_at="2025-05-01",
                    parent_source_id=root.id,
                )
            evidence = repository.save_evidence(
                run_id=run.id,
                source_id=source.id,
                quote=f"Fixture observation {root_index}-{document_index}.",
                locator="section 1",
                observed_at="2025-05-02",
                source_mode="FIXTURE",
            )
            evidence_items.append(evidence)
            repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")
    return run, claim, evidence_items


def _current_policy():
    return ValidationPolicy(freshness_cutoff="2025-01-01", freshness_required=True)


def test_two_current_independent_roots_allow_strong_confidence(repository):
    run, claim, _ = _claim_with_roots(repository, root_count=2)

    report = Validator(repository).validate_run(run.id, _current_policy())

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == "VALID"
    assert checked.confidence_level == "STRONG"
    assert report.confidence == "STRONG"


def test_three_documents_from_one_root_remain_moderate(repository):
    run, claim, _ = _claim_with_roots(
        repository, root_count=1, documents_per_root=3
    )

    report = Validator(repository).validate_run(run.id, _current_policy())

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.confidence_level == "MODERATE"


def test_blocking_gap_for_claim_prevents_strong_confidence(repository):
    run, claim, _ = _claim_with_roots(repository, root_count=2)
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="GAP",
            message="A required comparable metric is missing.",
            severity="BLOCKING",
            related_claim_id=claim.id,
        )
    )

    report = Validator(repository).validate_run(run.id, _current_policy())

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.confidence_level == "MODERATE"
