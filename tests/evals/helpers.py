from __future__ import annotations


def add_evidence(
    repository,
    run_id: str,
    *,
    url: str,
    quote: str = "FIXTURE: a research observation was recorded.",
    locator: str = "section 1",
    source_type: str = "REPORT",
    parent_source_id: str | None = None,
    published_at: str | None = "2026-01-15",
    observed_at: str | None = "2026-01-15",
    metric: str | None = None,
    value: str | int | float | None = None,
    unit: str | None = None,
    market: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    scope: str | None = None,
    method: str | None = None,
    direction: str | None = None,
):
    source = repository.save_source(
        run_id=run_id,
        url=url,
        title=f"Fixture source {url.rsplit('/', 1)[-1]}",
        publisher="Fixture publisher",
        published_at=published_at,
        source_type=source_type,
        parent_source_id=parent_source_id,
    )
    metadata = {"direction": direction} if direction is not None else {}
    evidence = repository.save_evidence(
        run_id=run_id,
        source_id=source.id,
        quote=quote,
        locator=locator,
        observed_at=observed_at,
        metric=metric,
        value=value,
        unit=unit,
        market=market,
        period_start=period_start,
        period_end=period_end,
        scope=scope,
        method=method,
        source_mode="FIXTURE",
        metadata=metadata,
    )
    return source, evidence


def add_claim(repository, run_id: str, *, text: str, target_metric: str | None, evidence_relations):
    claim = repository.save_claim(
        run_id=run_id,
        text=text,
        claim_type="INFERENCE",
        target_metric=target_metric,
    )
    for evidence, relation in evidence_relations:
        repository.link_claim_evidence(claim.id, evidence.id, relation)
    return claim
