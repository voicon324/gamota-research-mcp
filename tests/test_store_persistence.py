from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "store_fixture.json"


def _store_service_type():
    try:
        module = importlib.import_module("gamota_research.domain.store_service")
        return module.StoreService
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"StoreService persistence capability is missing: {error}")


def _fixture_provider():
    try:
        module = importlib.import_module(
            "gamota_research.domain.fixture_provider"
        )
        return module.FixtureStoreProvider(FIXTURE)
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"FixtureStoreProvider capability is missing: {error}")


def test_chart_snapshots_and_history_survive_database_reopen(database, repository):
    store_service_type = _store_service_type()
    run = repository.create_run("Persist synthetic chart observations")
    service = store_service_type(repository, _fixture_provider())

    service.get_chart_snapshot(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        limit=10,
    )
    service.get_chart_snapshot(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        limit=10,
    )
    database.close()

    try:
        database_module = importlib.import_module("gamota_research.db")
        repository_module = importlib.import_module("gamota_research.repository")
        reopened = database_module.Database(database.path)
        try:
            reopened_repository = repository_module.ResearchRepository(reopened)
            reopened_service = store_service_type(
                reopened_repository, _fixture_provider()
            )
            history = reopened_service.get_chart_history(
                run_id=run.id,
                store="google_play",
                country="VN",
                chart_type="top_free",
                game_id="synthetic-orbit-quest",
            )

            assert [item["observed_at"] for item in history["observations"]] == [
                "2026-10-01T00:00:00+00:00",
                "2026-10-15T00:00:00+00:00",
            ]
            assert history["observation_count"] == 2
            assert history["movement"] == {
                "previous_rank": 20,
                "current_rank": 8,
                "rank_change": 12,
                "observation_count": 2,
            }
        finally:
            reopened.close()
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"Persistent store history capability is missing: {error}")


def test_store_snapshot_tables_enforce_run_and_snapshot_foreign_keys(database):
    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as connection:
            connection.execute(
                """INSERT INTO store_snapshots
                   (id, run_id, provider, store, country, chart_type, observed_at,
                    source_mode, source_url, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "orphan-snapshot",
                    "missing-run",
                    "synthetic-store-fixture",
                    "google_play",
                    "VN",
                    "top_free",
                    "2026-10-15T00:00:00+00:00",
                    "FIXTURE",
                    "fixture://gamota/store/orphan",
                    "{}",
                ),
            )

    run = importlib.import_module("gamota_research.repository").ResearchRepository(
        database
    ).create_run("Check snapshot-item foreign key")
    service_module = importlib.import_module("gamota_research.domain.store_service")
    service = service_module.StoreService(
        importlib.import_module("gamota_research.repository").ResearchRepository(
            database
        ),
        _fixture_provider(),
    )
    snapshot = service.get_chart_snapshot(
        run_id=run.id,
        store="google_play",
        country="VN",
        chart_type="top_free",
        limit=10,
    )
    assert snapshot.snapshot_id

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as connection:
            connection.execute(
                """INSERT INTO store_snapshot_items
                   (snapshot_id, game_id, store_app_id, title, rank, genre, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "missing-snapshot",
                    "synthetic-orbit-quest",
                    "fixture.app.orbit-quest",
                    "Orbit Quest (synthetic test game)",
                    20,
                    "RPG",
                    "{}",
                ),
            )
