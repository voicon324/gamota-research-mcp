from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from ..enums import SourceMode
from .models import StoreChartItem, StoreChartObservation, StoreGame


class FixtureStoreProvider:
    """Deterministic synthetic store data. It never reports LIVE observations."""

    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not load store fixture: {error}") from error
        if not isinstance(data, dict) or data.get("generated_for_testing") is not True:
            raise ValueError("Store fixture must set generated_for_testing = true")
        if data.get("source_mode") != SourceMode.FIXTURE.value:
            raise ValueError("Store fixture source_mode must be FIXTURE")

        provider_name = data.get("provider")
        if not isinstance(provider_name, str) or not provider_name.strip():
            raise ValueError("Store fixture must declare a provider name")
        self._provider_name = provider_name.strip()
        self._lock = RLock()
        self._snapshot_offsets: dict[tuple[str, str, str], int] = {}

        self._games = tuple(
            self._game_from_record(record)
            for record in self._records(data, "store_games")
        )
        snapshots: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for record in self._records(data, "chart_snapshots"):
            if record.get("source_mode", SourceMode.FIXTURE.value) != SourceMode.FIXTURE.value:
                raise ValueError("Every fixture chart snapshot must use source_mode FIXTURE")
            key = (
                self._store(record.get("store")),
                self._country(record.get("country")),
                self._required_text(record, "chart_type"),
            )
            snapshots.setdefault(key, []).append(record)
        for records in snapshots.values():
            records.sort(key=lambda record: self._required_text(record, "observed_at"))
        self._chart_snapshots = snapshots

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def source_mode(self) -> SourceMode:
        return SourceMode.FIXTURE

    @staticmethod
    def _records(data: dict[str, Any], field: str) -> list[dict[str, Any]]:
        value = data.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ValueError(f"Store fixture {field} must be a list of objects")
        return value

    @staticmethod
    def _required_text(record: dict[str, Any], field: str) -> str:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Store fixture field {field} must be a non-empty string")
        return value.strip()

    @classmethod
    def _store(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("store must be a non-empty string")
        return value.strip().casefold()

    @classmethod
    def _country(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("country must be a non-empty string")
        return value.strip().upper()

    def _game_from_record(self, record: dict[str, Any]) -> StoreGame:
        if record.get("source_mode", SourceMode.FIXTURE.value) != SourceMode.FIXTURE.value:
            raise ValueError("Every fixture game must use source_mode FIXTURE")
        metadata = dict(record.get("metadata") or {})
        metadata["generated_for_testing"] = True
        return StoreGame(
            game_id=self._required_text(record, "game_id"),
            store_app_id=self._required_text(record, "store_app_id"),
            title=self._required_text(record, "title"),
            store=self._store(record.get("store")),
            country=self._country(record.get("country")),
            store_url=self._required_text(record, "store_url"),
            source_url=self._required_text(record, "source_url"),
            provider=self._provider_name,
            source_mode=SourceMode.FIXTURE,
            observed_at=self._required_text(record, "observed_at"),
            developer=record.get("developer"),
            publisher=record.get("publisher"),
            genre=record.get("genre"),
            metadata=metadata,
        )

    def search_apps(self, *, store: str, country: str, query: str) -> list[StoreGame]:
        normalized_store = self._store(store)
        normalized_country = self._country(country)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        needle = query.strip().casefold()
        return [
            game
            for game in self._games
            if game.store.casefold() == normalized_store
            and game.country == normalized_country
            and needle
            in " ".join(
                value or ""
                for value in (
                    game.game_id,
                    game.store_app_id,
                    game.title,
                    game.developer,
                    game.publisher,
                    game.genre,
                )
            ).casefold()
        ]

    def get_game_details(self, *, store: str, country: str, game_id: str) -> StoreGame:
        normalized_store = self._store(store)
        normalized_country = self._country(country)
        if not isinstance(game_id, str) or not game_id.strip():
            raise ValueError("game_id must be a non-empty string")
        for game in self._games:
            if (
                game.game_id == game_id.strip()
                and game.store.casefold() == normalized_store
                and game.country == normalized_country
            ):
                return game
        raise KeyError(f"Store game not found in fixture: {game_id}")

    def get_chart_snapshot(
        self,
        *,
        store: str,
        country: str,
        chart_type: str,
        limit: int | None = None,
    ) -> StoreChartObservation:
        normalized_store = self._store(store)
        normalized_country = self._country(country)
        if not isinstance(chart_type, str) or not chart_type.strip():
            raise ValueError("chart_type must be a non-empty string")
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
        ):
            raise ValueError("limit must be a positive integer")
        key = (normalized_store, normalized_country, chart_type.strip())
        with self._lock:
            records = self._chart_snapshots.get(key, [])
            offset = self._snapshot_offsets.get(key, 0)
            if offset >= len(records):
                raise KeyError("No more scheduled synthetic chart snapshots")
            record = records[offset]
            self._snapshot_offsets[key] = offset + 1

        item_records = self._records({"items": record.get("items", [])}, "items")
        items = tuple(
            StoreChartItem(
                game_id=self._required_text(item, "game_id"),
                store_app_id=self._required_text(item, "store_app_id"),
                title=self._required_text(item, "title"),
                rank=self._positive_rank(item.get("rank")),
                genre=item.get("genre"),
                metadata={"generated_for_testing": True},
            )
            for item in item_records
        )
        if limit is not None:
            items = items[:limit]
        return StoreChartObservation(
            provider=self.provider_name,
            store=normalized_store,
            country=normalized_country,
            chart_type=key[2],
            observed_at=self._required_text(record, "observed_at"),
            source_mode=SourceMode.FIXTURE,
            source_url=self._required_text(record, "source_url"),
            items=items,
            metadata={"generated_for_testing": True},
        )

    @staticmethod
    def _positive_rank(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("chart rank must be a positive integer")
        return value
