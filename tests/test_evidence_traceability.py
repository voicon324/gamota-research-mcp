from __future__ import annotations


def test_claim_trace_returns_evidence_and_source_quote(repository):
    run = repository.create_run("Find a growth signal for a game genre")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/report",
        title="Sample report",
        publisher="Sample Publisher",
        source_type="REPORT",
        accessed_at="2026-10-15T00:00:00+00:00",
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="FIXTURE: installs increased in the sampled market.",
        locator="page 4, paragraph 2",
        metric="downloads",
        unit="installs",
        market="Example market",
        period_start="2025-01-01",
        period_end="2025-06-30",
        scope="FIXTURE sample only",
        method="publisher estimate",
        source_mode="FIXTURE",
    )
    claim = repository.save_claim(
        run_id=run.id,
        text="FIXTURE: the sampled genre had rising downloads.",
        claim_type="INFERENCE",
    )
    repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")

    trace = repository.get_claim_trace(claim.id)

    assert trace["claim"]["id"] == claim.id
    assert len(trace["evidence"]) == 1
    traced_evidence = trace["evidence"][0]
    assert traced_evidence["evidence"]["id"] == evidence.id
    assert traced_evidence["evidence"]["quote"].startswith("FIXTURE:")
    assert traced_evidence["evidence"]["locator"] == "page 4, paragraph 2"
    assert traced_evidence["source"]["id"] == source.id
    assert traced_evidence["source"]["url"] == "https://example.test/report"


def test_database_enforces_run_source_and_evidence_foreign_keys(database):
    with database.connection() as connection:
        enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1


def test_derived_source_keeps_primary_root(repository):
    run = repository.create_run("Track a cited report back to its origin")
    primary = repository.save_source(
        run_id=run.id,
        url="https://example.test/original-report",
        title="Original report",
        source_type="REPORT",
    )
    secondary = repository.save_source(
        run_id=run.id,
        url="https://example.test/news-article",
        title="Article citing the report",
        source_type="NEWS",
        parent_source_id=primary.id,
    )

    assert primary.root_source_id == primary.id
    assert secondary.parent_source_id == primary.id
    assert secondary.root_source_id == primary.id
