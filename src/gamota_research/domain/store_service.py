from __future__ import annotations

from typing import Any

from ..enums import SourceMode
from ..repository import ResearchRepository
from .models import StoreChartSnapshot
from .provider import StoreProvider


class StoreService:
    """Coordinates store-provider observations and their persisted history."""

    def __init__(self, repository: ResearchRepository, provider: StoreProvider):
        self.repository = repository
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.provider_name

    @property
    def source_mode(self) -> SourceMode | str:
        return self.provider.source_mode

    def search_apps(self, *, store: str, country: str, query: str):
        return self.provider.search_apps(store=store, country=country, query=query)

    def get_game_details(self, *, store: str, country: str, game_id: str):
        return self.provider.get_game_details(
            store=store, country=country, game_id=game_id
        )

    def get_chart_snapshot(
        self,
        *,
        run_id: str,
        store: str,
        country: str,
        chart_type: str,
        limit: int | None = None,
    ) -> StoreChartSnapshot:
        if self.repository.get_run(run_id) is None:
            raise KeyError(f"Research run not found: {run_id}")
        observation = self.provider.get_chart_snapshot(
            store=store,
            country=country,
            chart_type=chart_type,
            limit=limit,
        )
        snapshot = StoreChartSnapshot(
            run_id=run_id,
            provider=observation.provider,
            store=observation.store,
            country=observation.country,
            chart_type=observation.chart_type,
            observed_at=observation.observed_at,
            source_mode=observation.source_mode,
            source_url=observation.source_url,
            items=observation.items,
            metadata=observation.metadata,
        )
        return self.repository.save_store_chart_snapshot(snapshot)

    def get_chart_history(
        self,
        *,
        run_id: str,
        store: str,
        country: str,
        chart_type: str,
        game_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        if self.repository.get_run(run_id) is None:
            raise KeyError(f"Research run not found: {run_id}")
        observations = self.repository.list_store_chart_history(
            run_id=run_id,
            store=store,
            country=country,
            chart_type=chart_type,
            game_id=game_id,
            start=start,
            end=end,
        )
        observation_count = len(observations)
        movement = None
        if observation_count >= 2:
            previous = observations[-2]
            current = observations[-1]
            movement = {
                "previous_rank": previous["rank"],
                "current_rank": current["rank"],
                "rank_change": previous["rank"] - current["rank"],
                "observation_count": observation_count,
            }
        latest = observations[-1] if observations else None
        return {
            "run_id": run_id,
            "store": store,
            "country": country,
            "chart_type": chart_type,
            "game_id": game_id,
            "provider": latest["provider"] if latest else self.provider_name,
            "source_mode": latest["source_mode"] if latest else self.source_mode,
            "metric": "store_rank",
            "observations": observations,
            "observation_count": observation_count,
            "movement": movement,
            "insufficient_history": observation_count < 2,
        }
