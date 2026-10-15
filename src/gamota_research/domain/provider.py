from __future__ import annotations

from typing import Protocol

from ..enums import SourceMode
from .models import StoreChartObservation, StoreGame


class StoreProvider(Protocol):
    """Provider contract ready for a later live adapter."""

    @property
    def provider_name(self) -> str: ...

    @property
    def source_mode(self) -> SourceMode | str: ...

    def search_apps(
        self, *, store: str, country: str, query: str
    ) -> list[StoreGame]: ...

    def get_game_details(
        self, *, store: str, country: str, game_id: str
    ) -> StoreGame: ...

    def get_chart_snapshot(
        self, *, store: str, country: str, chart_type: str, limit: int | None
    ) -> StoreChartObservation: ...
