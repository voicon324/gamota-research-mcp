from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.request import HTTPRedirectHandler, build_opener

from ..enums import SourceMode
from .models import StoreChartItem, StoreChartObservation, StoreGame


class AppleRssSourceError(ValueError):
    """An explicit failure while reading or validating Apple's public RSS feed."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class AppleRssStoreProvider:
    """Read only Apple's public Vietnam Top Free/Top Paid app RSS feeds."""

    _BASE_URL = "https://rss.marketingtools.apple.com/api/v2/vn/apps"
    _FEED_PATHS = {"top_free": "top-free", "top_paid": "top-paid"}
    _FEED_LIMIT = 50

    def __init__(
        self,
        *,
        fetch_json: Callable[[str], Any] | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self._fetch_json_override = fetch_json
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "apple_rss"

    @property
    def source_mode(self) -> SourceMode:
        return SourceMode.LIVE

    def get_chart_snapshot(
        self,
        *,
        store: str,
        country: str,
        chart_type: str,
        limit: int | None,
    ) -> StoreChartObservation:
        self._validate_market(store, country)
        normalized_chart_type = self._normalize_chart_type(chart_type)
        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            or limit > self._FEED_LIMIT
        ):
            raise ValueError(f"limit must be between 1 and {self._FEED_LIMIT}")

        source_url, feed_updated, records = self._read_feed(normalized_chart_type)
        visible_records = records if limit is None else records[:limit]
        items = tuple(
            self._chart_item(record, index, normalized_chart_type)
            for index, record in enumerate(visible_records, start=1)
        )
        return StoreChartObservation(
            provider=self.provider_name,
            store="app_store",
            country="VN",
            chart_type=normalized_chart_type,
            observed_at=feed_updated,
            source_mode=SourceMode.LIVE,
            source_url=source_url,
            items=items,
            metadata={
                "feed_title": "Top Free Apps" if normalized_chart_type == "top_free" else "Top Paid Apps",
                "feed_updated": feed_updated,
                "feed_result_count": len(records),
                "source_mode": SourceMode.LIVE.value,
            },
        )

    def search_apps(self, *, store: str, country: str, query: str) -> list[StoreGame]:
        self._validate_market(store, country)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        needle = query.strip().casefold()
        matches: list[StoreGame] = []
        seen_ids: set[str] = set()
        for chart_type in self._FEED_PATHS:
            source_url, feed_updated, records = self._read_feed(chart_type)
            for record in records:
                game = self._game_from_record(
                    record,
                    chart_type=chart_type,
                    observed_at=feed_updated,
                    source_url=source_url,
                )
                searchable = " ".join(
                    [
                        game.store_app_id,
                        game.title,
                        game.developer or "",
                        game.genre or "",
                    ]
                ).casefold()
                if needle in searchable and game.store_app_id not in seen_ids:
                    matches.append(game)
                    seen_ids.add(game.store_app_id)
        return matches

    def get_game_details(
        self, *, store: str, country: str, game_id: str
    ) -> StoreGame:
        self._validate_market(store, country)
        if not isinstance(game_id, str) or not game_id.strip():
            raise ValueError("game_id must be a non-empty string")
        requested_id = game_id.strip()
        if requested_id.startswith("apple_rss:"):
            requested_id = requested_id.removeprefix("apple_rss:")
        for chart_type in self._FEED_PATHS:
            source_url, feed_updated, records = self._read_feed(chart_type)
            for record in records:
                app_id = self._required_id(record.get("id"), "result.id")
                if app_id == requested_id:
                    return self._game_from_record(
                        record,
                        chart_type=chart_type,
                        observed_at=feed_updated,
                        source_url=source_url,
                    )
        raise KeyError(f"Store app not found in Apple RSS feeds: {game_id}")

    def _read_feed(self, chart_type: str) -> tuple[str, str, list[dict[str, Any]]]:
        feed_path = self._FEED_PATHS[chart_type]
        source_url = (
            f"{self._BASE_URL}/{feed_path}/{self._FEED_LIMIT}/apps.json"
        )
        try:
            if self._fetch_json_override is not None:
                payload = self._fetch_json_override(source_url)
            else:
                opener = build_opener(_RejectRedirects)
                with opener.open(source_url, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise AppleRssSourceError(
                f"SOURCE_FAILURE: Apple RSS request failed for {source_url}: {error}"
            ) from error

        try:
            if not isinstance(payload, dict):
                raise ValueError("response must be a JSON object")
            feed = payload.get("feed")
            if not isinstance(feed, dict):
                raise ValueError("feed must be an object")
            if str(feed.get("country", "")).casefold() != "vn":
                raise ValueError("feed country must be vn")
            feed_updated = feed.get("updated")
            if not isinstance(feed_updated, str) or not feed_updated.strip():
                raise ValueError("feed.updated must be a non-empty timestamp")
            results = feed.get("results")
            if not isinstance(results, list) or any(
                not isinstance(result, dict) for result in results
            ):
                raise ValueError("feed.results must be a list of objects")
        except (TypeError, ValueError) as error:
            raise AppleRssSourceError(
                f"SOURCE_FAILURE: invalid Apple RSS payload from {source_url}: {error}"
            ) from error
        return source_url, feed_updated.strip(), results

    def _chart_item(
        self, record: dict[str, Any], rank: int, chart_type: str
    ) -> StoreChartItem:
        app_id = self._required_id(record.get("id"), "result.id")
        title = self._required_text(record.get("name"), "result.name")
        genres = self._normalize_genres(record.get("genres", []))
        genre = genres[0] if genres else "UNKNOWN"
        metadata = {
            "chart_type": chart_type,
            "artist_name": record.get("artistName"),
            "kind": record.get("kind"),
            "release_date": record.get("releaseDate"),
            "genres": genres,
            "store_url": record.get("url"),
        }
        return StoreChartItem(
            game_id=f"apple_rss:{app_id}",
            store_app_id=app_id,
            title=title,
            rank=rank,
            genre=genre,
            metadata=metadata,
        )

    def _game_from_record(
        self,
        record: dict[str, Any],
        *,
        chart_type: str,
        observed_at: str,
        source_url: str,
    ) -> StoreGame:
        app_id = self._required_id(record.get("id"), "result.id")
        title = self._required_text(record.get("name"), "result.name")
        store_url = self._required_text(record.get("url"), "result.url")
        genres = self._normalize_genres(record.get("genres", []))
        artist = record.get("artistName")
        if artist is not None and not isinstance(artist, str):
            raise AppleRssSourceError(
                "SOURCE_FAILURE: invalid Apple RSS payload: result.artistName must be text"
            )
        return StoreGame(
            game_id=f"apple_rss:{app_id}",
            store_app_id=app_id,
            title=title,
            store="app_store",
            country="VN",
            store_url=store_url,
            source_url=source_url,
            provider=self.provider_name,
            source_mode=SourceMode.LIVE,
            observed_at=observed_at,
            developer=artist,
            genre=genres[0] if genres else "UNKNOWN",
            metadata={
                "chart_type": chart_type,
                "feed_updated": observed_at,
                "genres": genres,
                "kind": record.get("kind"),
                "release_date": record.get("releaseDate"),
            },
        )

    @staticmethod
    def _normalize_genres(value: Any) -> list[str]:
        if not isinstance(value, list):
            raise AppleRssSourceError(
                "SOURCE_FAILURE: invalid Apple RSS payload: result.genres must be a list"
            )
        normalized: list[str] = []
        for genre in value:
            if isinstance(genre, str):
                name = genre.strip()
            elif isinstance(genre, dict) and isinstance(genre.get("name"), str):
                name = genre["name"].strip()
            else:
                raise AppleRssSourceError(
                    "SOURCE_FAILURE: invalid Apple RSS payload: each result genre must be text or an object with a name"
                )
            if name:
                normalized.append(name)
        return normalized

    @staticmethod
    def _normalize_chart_type(chart_type: str) -> str:
        if not isinstance(chart_type, str):
            raise ValueError("chart_type must be a string")
        normalized = chart_type.strip().casefold()
        if normalized not in AppleRssStoreProvider._FEED_PATHS:
            raise ValueError("Apple RSS supports only top_free and top_paid")
        return normalized

    @staticmethod
    def _validate_market(store: str, country: str) -> None:
        if not isinstance(store, str) or store.strip().casefold() != "app_store":
            raise ValueError("Apple RSS supports only store=app_store")
        if not isinstance(country, str) or country.strip().upper() != "VN":
            raise ValueError("Apple RSS supports only country=VN")

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AppleRssSourceError(
                f"SOURCE_FAILURE: invalid Apple RSS payload: {field} must be non-empty text"
            )
        return value.strip()

    @staticmethod
    def _required_id(value: Any, field: str) -> str:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise AppleRssSourceError(
                f"SOURCE_FAILURE: invalid Apple RSS payload: {field} must be a string or integer"
            )
        normalized = str(value).strip()
        if not normalized:
            raise AppleRssSourceError(
                f"SOURCE_FAILURE: invalid Apple RSS payload: {field} must be non-empty"
            )
        return normalized
