from __future__ import annotations

import importlib
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "store_fixture.json"


def _store_service_type():
    try:
        module = importlib.import_module("gamota_research.domain.store_service")
        return module.StoreService
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"StoreService rank semantics are missing: {error}")


def _fixture_provider():
    try:
        module = importlib.import_module(
            "gamota_research.domain.fixture_provider"
        )
        return module.FixtureStoreProvider(FIXTURE)
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"FixtureStoreProvider capability is missing: {error}")


def test_one_chart_observation_does_not_claim_rank_momentum(repository):
    run = repository.create_run("A single rank observation is not a trend")
    service = _store_service_type()(repository, _fixture_provider())
    service.get_chart_snapshot(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        limit=10,
    )

    history = service.get_chart_history(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        game_id="synthetic-orbit-quest",
    )

    assert history["observation_count"] == 1
    assert history["movement"] is None
    assert history["insufficient_history"] is True


def test_two_observations_report_rank_change_without_market_metric_inference(
    repository,
):
    run = repository.create_run("Compare two synthetic store-rank observations")
    service = _store_service_type()(repository, _fixture_provider())
    for _ in range(2):
        service.get_chart_snapshot(
            run_id=run.id,
            store="google_play",
            country="VN",
            chart_type="top_free",
            limit=10,
        )

    history = service.get_chart_history(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        game_id="synthetic-orbit-quest",
    )

    assert history["observation_count"] == 2
    assert history["movement"] == {
        "previous_rank": 20,
        "current_rank": 8,
        "rank_change": 12,
        "observation_count": 2,
    }
    assert history["metric"] == "store_rank"
    assert history["source_mode"] == "FIXTURE"
    assert "revenue" not in history
    assert "downloads" not in history
    assert "DAU" not in history
