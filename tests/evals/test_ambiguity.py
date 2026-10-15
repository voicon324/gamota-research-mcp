from __future__ import annotations

from gamota_research.models import ResearchIssue
from gamota_research.validator import Validator


def test_blocking_ambiguity_requests_clarification_without_fabricating_claim(repository):
    run = repository.create_run("Which genre is best?")
    repository.save_issue(
        ResearchIssue(
            run_id=run.id,
            code="AMBIGUITY",
            message="The decision criterion and market scope are unspecified.",
            severity="BLOCKING",
            metadata={"missing_fields": ["decision_criterion", "market_scope"]},
        )
    )

    report = Validator(repository).validate_run(run.id)

    assert report.status == "NEEDS_CLARIFICATION"
    assert repository.get_run(run.id).status == "NEEDS_CLARIFICATION"
    assert repository.list_claims(run.id) == []
    issue = next(item for item in report.issues if item.code == "AMBIGUITY")
    assert issue.severity == "BLOCKING"
    assert issue.metadata["missing_fields"] == ["decision_criterion", "market_scope"]
