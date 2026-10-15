from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..enums import SourceMode
from ..models import new_id


@dataclass(frozen=True)
class StoreGame:
    game_id: str
    store_app_id: str
    title: str
    store: str
    country: str
    store_url: str
    source_url: str
    provider: str
    source_mode: SourceMode | str
    observed_at: str
    developer: str | None = None
    publisher: str | None = None
    genre: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreChartItem:
    game_id: str
    store_app_id: str
    title: str
    rank: int
    genre: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreChartObservation:
    provider: str
    store: str
    country: str
    chart_type: str
    observed_at: str
    source_mode: SourceMode | str
    source_url: str
    items: tuple[StoreChartItem, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreChartSnapshot:
    run_id: str
    provider: str
    store: str
    country: str
    chart_type: str
    observed_at: str
    source_mode: SourceMode | str
    source_url: str
    items: tuple[StoreChartItem, ...]
    snapshot_id: str = field(default_factory=new_id)
    metadata: dict[str, Any] = field(default_factory=dict)
