from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "store_fixture.json"


def _fixture_provider_type():
    try:
        module = importlib.import_module(
            "gamota_research.domain.fixture_provider"
        )
        return module.FixtureStoreProvider
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"FixtureStoreProvider capability is missing: {error}")


def test_fixture_search_returns_only_matching_games_with_fixture_provenance():
    provider = _fixture_provider_type()(FIXTURE)

    games = provider.search_apps(
        store="google_play", country="VN", query="orbit"
    )

    assert [game.game_id for game in games] == ["synthetic-orbit-quest"]
    assert games[0].source_mode == "FIXTURE"
    assert games[0].provider == "synthetic-store-fixture"
    assert games[0].source_url.startswith("fixture://")
    assert games[0].metadata["generated_for_testing"] is True


def test_fixture_game_details_include_store_market_and_observation_provenance():
    provider = _fixture_provider_type()(FIXTURE)

    game = provider.get_game_details(
        store="google_play",
        country="VN",
        game_id="synthetic-orbit-quest",
    )

    assert game.store_app_id == "fixture.app.orbit-quest"
    assert game.genre == "RPG"
    assert game.store == "google_play"
    assert game.country == "VN"
    assert game.provider == "synthetic-store-fixture"
    assert game.source_mode == "FIXTURE"
    assert game.observed_at == "2026-10-15T00:00:00+00:00"


def test_fixture_chart_provider_returns_deterministic_historical_observations():
    provider = _fixture_provider_type()(FIXTURE)

    earlier = provider.get_chart_snapshot(
        store="google_play", country="VN", chart_type="top_free", limit=10
    )
    later = provider.get_chart_snapshot(
        store="google_play", country="VN", chart_type="top_free", limit=10
    )

    assert earlier.observed_at == "2026-10-01T00:00:00+00:00"
    assert later.observed_at == "2026-10-15T00:00:00+00:00"
    assert earlier.items[0].rank == 20
    assert later.items[0].rank == 8
    assert earlier.source_mode == later.source_mode == "FIXTURE"
    assert all(item.title.endswith("(synthetic test game)") for item in later.items)


def test_fixture_provider_rejects_data_not_explicitly_marked_for_testing(tmp_path):
    provider_type = _fixture_provider_type()
    fixture_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture_data["generated_for_testing"] = False
    unmarked = tmp_path / "unmarked-store-data.json"
    unmarked.write_text(json.dumps(fixture_data), encoding="utf-8")

    with pytest.raises(ValueError, match="generated_for_testing"):
        provider_type(unmarked)
