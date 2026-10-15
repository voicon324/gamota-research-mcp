from __future__ import annotations

from gamota_research.models import ResearchIssue
from gamota_research.validator import Validator


def test_source_failure_is_recorded_and_run_remains_inspectable(repository):
    run = repository.create_run("Collect public market evidence")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/unavailable-source",
        title="Unavailable fixture source",
        source_type="OFFICIAL",
    )
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="SOURCE_FAILURE",
            message="The source returned a timeout.",
            severity="ERROR",
            source_id=source.id,
            metadata={"provider": "fixture-failure", "retryable": True},
        )
    )

    report = Validator(repository).validate_run(run.id)

    assert repository.get_run(run.id) is not None
    assert repository.get_run(run.id).status == "INSUFFICIENT_DATA"
    assert report.status == "INSUFFICIENT_DATA"
    failure = next(item for item in repository.list_issues(run.id) if item.code == "SOURCE_FAILURE")
    assert failure.source_id == source.id
    assert failure.metadata == {"provider": "fixture-failure", "retryable": True}
    assert repository.get_source(source.id).id == source.id
