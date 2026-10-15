from __future__ import annotations

import pytest

from gamota_research.contract import ResearchContract


def test_research_contract_persists_across_database_reopen(database, repository):
    run = repository.create_run("Assess recent mobile game signals in Vietnam")
    contract = {
        "question": run.question,
        "decision_goal": "Identify game segments worth monitoring.",
        "geography": ["VN"],
        "time_scope": {"kind": "trailing_months", "months": 12},
        "metrics": ["store_rank", "revenue_growth"],
        "segments": ["mobile games"],
        "assumptions": ["recent means the trailing 12 months"],
        "evidence_slots": ["market_evidence", "store_momentum"],
        "freshness_cutoff": "2025-10-15",
        "planned_query_budget": 10,
        "domain_tool_budget": 10,
        "research_round_budget": 2,
    }

    repository.set_research_contract(run.id, contract)
    database.close()

    from gamota_research.db import Database
    from gamota_research.repository import ResearchRepository

    reopened = Database(database.path)
    try:
        stored = ResearchRepository(reopened).get_research_contract(run.id)
        assert stored == contract
    finally:
        reopened.close()


def test_contract_has_bounded_mvp_budget_defaults():
    contract = ResearchContract.from_value({"question": "A bounded research task"})

    assert contract.planned_query_budget == 10
    assert contract.domain_tool_budget == 10
    assert contract.research_round_budget == 2


def test_contract_normalizes_slot_names_and_rejects_invalid_budget_or_cutoff():
    contract = ResearchContract.from_value(
        {
            "question": "  Check a market signal  ",
            "evidence_slots": [" market_evidence ", "market_evidence"],
        }
    )
    assert contract.question == "Check a market signal"
    assert contract.evidence_slots == ("market_evidence",)

    with pytest.raises(ValueError, match="positive integer"):
        ResearchContract.from_value({"question": "Check budget", "planned_query_budget": 0})
    with pytest.raises(ValueError, match="ISO date"):
        ResearchContract.from_value({"question": "Check freshness", "freshness_cutoff": "recent"})
