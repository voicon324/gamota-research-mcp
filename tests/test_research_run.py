from __future__ import annotations

import pytest


def test_research_run_survives_database_reopen(database, repository):
    from gamota_research.db import Database
    from gamota_research.repository import ResearchRepository

    run = repository.create_run("Which mobile genres show growth signals?")
    database_path = database.path
    database.close()

    reopened = Database(database_path)
    try:
        loaded = ResearchRepository(reopened).get_run(run.id)
    finally:
        reopened.close()

    assert loaded.id == run.id
    assert loaded.question == "Which mobile genres show growth signals?"
    assert loaded.status == "CREATED"
    assert loaded.created_at


def test_all_six_core_entities_are_importable():
    try:
        from gamota_research.models import (
            Claim,
            ClaimEvidence,
            Evidence,
            ResearchIssue,
            ResearchRun,
            Source,
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"research models are not implemented yet: {error}")

    assert all((ResearchRun, Source, Evidence, Claim, ClaimEvidence, ResearchIssue))
