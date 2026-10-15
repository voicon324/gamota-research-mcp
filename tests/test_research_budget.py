from __future__ import annotations

import pytest

from gamota_research.service import ResearchService


def _contract(question: str):
    return {
        "question": question,
        "planned_query_budget": 10,
        "domain_tool_budget": 10,
        "research_round_budget": 2,
    }


def test_host_reported_search_count_is_distinguished_from_enforced_domain_calls(repository):
    service = ResearchService(repository)
    run = service.create_run("Keep host search counts explicit")
    service.set_research_contract(run.id, _contract(run.question))
    service.update_research_progress(
        run.id,
        reported_search_count=4,
        domain_tool_call_count=3,
        research_round=1,
    )

    status = service.get_research_budget_status(run.id)

    assert status["reported_search_count"] == 4
    assert status["planned_query_budget"] == 10
    assert status["domain_tool_call_count"] == 3
    assert status["within_budget"] is True
    assert "actual_search_count" not in status


def test_query_domain_and_round_limits_report_exhausted(repository):
    service = ResearchService(repository)
    run = service.create_run("Stop when the configured budgets are reached")
    service.set_research_contract(run.id, _contract(run.question))
    service.update_research_progress(
        run.id,
        reported_search_count=10,
        domain_tool_call_count=10,
        research_round=2,
    )

    status = service.get_research_budget_status(run.id)

    assert status["query_budget_exhausted"] is True
    assert status["domain_budget_exhausted"] is True
    assert status["round_budget_exhausted"] is True
    assert status["within_budget"] is True


def test_budget_is_exceeded_only_after_a_counter_passes_its_limit(repository):
    service = ResearchService(repository)
    run = service.create_run("Exhausted budget can remain valid")
    service.set_research_contract(run.id, _contract(run.question))
    service.update_research_progress(
        run.id,
        reported_search_count=11,
        domain_tool_call_count=11,
        research_round=3,
    )

    status = service.get_research_budget_status(run.id)

    assert status["query_budget_exhausted"] is True
    assert status["domain_budget_exhausted"] is True
    assert status["round_budget_exhausted"] is True
    assert status["within_budget"] is False


def test_progress_counters_are_non_negative_and_monotonic(repository):
    service = ResearchService(repository)
    run = service.create_run("Progress counters cannot be refunded")
    service.set_research_contract(run.id, _contract(run.question))
    service.update_research_progress(run.id, reported_search_count=4)

    with pytest.raises(ValueError, match="cannot decrease"):
        service.update_research_progress(run.id, reported_search_count=3)
    with pytest.raises(ValueError, match="non-negative integer"):
        service.update_research_progress(run.id, domain_tool_call_count=-1)


def test_research_progress_and_budget_status_persist_after_database_reopen(
    database, repository
):
    service = ResearchService(repository)
    run = service.create_run("Persist bounded research progress")
    service.set_research_contract(run.id, _contract(run.question))
    service.update_research_progress(
        run.id,
        reported_search_count=4,
        domain_tool_call_count=3,
        research_round=1,
    )
    database.close()

    from gamota_research.db import Database
    from gamota_research.repository import ResearchRepository

    reopened = Database(database.path)
    try:
        status = ResearchRepository(reopened).get_research_budget_status(run.id)
        assert status["reported_search_count"] == 4
        assert status["domain_tool_call_count"] == 3
        assert status["research_round"] == 1
        assert status["within_budget"] is True
    finally:
        reopened.close()
