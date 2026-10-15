from __future__ import annotations

import json
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import anyio
import pytest
from mcp import ClientSession

from gamota_research.domain.apple_rss_provider import AppleRssStoreProvider


@asynccontextmanager
async def _protocol_session(server):
    client_to_server_send, server_receive = anyio.create_memory_object_stream(0)
    server_to_client_send, client_receive = anyio.create_memory_object_stream(0)
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(
            server._lowlevel_server.run,
            server_receive,
            server_to_client_send,
            server._lowlevel_server.create_initialization_options(),
        )
        try:
            async with ClientSession(client_receive, client_to_server_send) as session:
                await session.initialize()
                yield session
        finally:
            task_group.cancel_scope.cancel()


def _feed(*results, title="Top Free Apps"):
    return {
        "feed": {
            "title": title,
            "country": "vn",
            "updated": "2026-10-15T00:00:00+00:00",
            "results": list(results),
        }
    }


def _app(app_id, name, *, genres=None, artist="Studio"):
    return {
        "id": str(app_id),
        "name": name,
        "artistName": artist,
        "url": f"https://apps.apple.com/vn/app/app/id{app_id}",
        "genres": genres or [],
        "kind": "software",
        "releaseDate": "2026-01-02",
    }


def test_top_free_chart_normalizes_official_feed_as_live_observation():
    feed_updated = "2026-10-15T00:00:00+00:00"
    payload = {
        "feed": {
            "title": "Top Free Apps",
            "country": "vn",
            "updated": feed_updated,
            "results": [
                {
                    "id": "12345",
                    "name": "Example App",
                    "artistName": "Example Studio",
                    "url": "https://apps.apple.com/vn/app/example/id12345",
                    "genres": [],
                    "kind": "software",
                    "releaseDate": "2026-01-02",
                }
            ],
        }
    }
    requested_urls: list[str] = []

    def fetch_json(url: str):
        requested_urls.append(url)
        return payload

    provider = AppleRssStoreProvider(fetch_json=fetch_json)

    observation = provider.get_chart_snapshot(
        store="app_store", country="VN", chart_type="top_free", limit=10
    )

    assert requested_urls == [
        "https://rss.marketingtools.apple.com/api/v2/vn/apps/top-free/50/apps.json"
    ]
    assert observation.provider == "apple_rss"
    assert observation.source_mode == "LIVE"
    assert observation.store == "app_store"
    assert observation.country == "VN"
    assert observation.chart_type == "top_free"
    assert observation.source_url == requested_urls[0]
    assert observation.observed_at == feed_updated
    assert observation.items[0].store_app_id == "12345"
    assert observation.items[0].rank == 1
    assert observation.items[0].genre == "UNKNOWN"
    assert observation.items[0].metadata["kind"] == "software"


def test_search_apps_searches_only_supported_official_feeds_and_deduplicates_ids():
    feeds = {
        "top-free": _feed(
            _app("11", "Sky Quest", genres=["Games", "Adventure"]),
            _app("12", "Other App"),
        ),
        "top-paid": _feed(
            _app("11", "Sky Quest", genres=["Games", "Adventure"]),
            _app("13", "Sky Puzzle"),
            title="Top Paid Apps",
        ),
    }
    requested_urls: list[str] = []

    def fetch_json(url: str):
        requested_urls.append(url)
        return feeds["top-free" if "top-free" in url else "top-paid"]

    provider = AppleRssStoreProvider(fetch_json=fetch_json)

    games = provider.search_apps(store="app_store", country="VN", query="sky")

    assert len(requested_urls) == 2
    assert [game.store_app_id for game in games] == ["11", "13"]
    assert games[0].game_id == "apple_rss:11"
    assert games[0].genre == "Games"
    assert games[0].metadata["chart_type"] == "top_free"
    assert games[1].metadata["chart_type"] == "top_paid"
    assert all(game.source_mode == "LIVE" for game in games)


def test_game_details_search_supported_feeds_and_return_not_found_explicitly():
    feeds = {
        "top-free": _feed(_app("21", "Free Game")),
        "top-paid": _feed(_app("22", "Paid Game", genres=["Strategy"]), title="Top Paid Apps"),
    }

    def fetch_json(url: str):
        return feeds["top-free" if "top-free" in url else "top-paid"]

    provider = AppleRssStoreProvider(fetch_json=fetch_json)

    game = provider.get_game_details(
        store="app_store", country="VN", game_id="apple_rss:22"
    )

    assert game.store_app_id == "22"
    assert game.title == "Paid Game"
    assert game.genre == "Strategy"
    assert game.source_mode == "LIVE"
    assert game.provider == "apple_rss"
    assert game.observed_at == "2026-10-15T00:00:00+00:00"
    assert game.source_url.endswith("/top-paid/50/apps.json")

    with pytest.raises(KeyError, match="not found in Apple RSS feeds"):
        provider.get_game_details(
            store="app_store", country="VN", game_id="apple_rss:absent"
        )


def test_feed_genre_objects_use_their_published_name_without_guessing():
    payload = _feed(
        _app(
            "31",
            "Genre App",
            genres=[
                {
                    "genreId": "6014",
                    "name": "Games",
                    "url": "https://apps.apple.com/vn/genre/games/id6014",
                }
            ],
        )
    )
    provider = AppleRssStoreProvider(fetch_json=lambda _url: payload)

    game = provider.get_game_details(
        store="app_store", country="VN", game_id="31"
    )

    assert game.genre == "Games"
    assert game.metadata["genres"] == ["Games"]


@pytest.mark.parametrize("chart_type", ["top_grossing", "games_only", "genre_growth"])
def test_unsupported_chart_types_are_rejected_without_fetching(chart_type):
    calls = []
    provider = AppleRssStoreProvider(fetch_json=lambda url: calls.append(url))

    with pytest.raises(ValueError, match="only top_free and top_paid"):
        provider.get_chart_snapshot(
            store="app_store", country="VN", chart_type=chart_type, limit=10
        )

    assert calls == []


def test_network_timeout_is_reported_as_source_failure_without_fixture_fallback():
    def timeout(_url):
        raise TimeoutError("simulated timeout")

    provider = AppleRssStoreProvider(fetch_json=timeout)

    with pytest.raises(ValueError, match="SOURCE_FAILURE.*simulated timeout"):
        provider.get_chart_snapshot(
            store="app_store", country="VN", chart_type="top_free", limit=10
        )


def test_default_transport_does_not_follow_redirects(monkeypatch):
    requests: list[str] = []
    feed_bytes = json.dumps(_feed(_app("41", "Redirected App"))).encode("utf-8")

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if self.path.endswith("/top-free/50/apps.json"):
                self.send_response(302)
                self.send_header("Location", "/redirect-target")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(feed_bytes)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(
            AppleRssStoreProvider,
            "_BASE_URL",
            f"http://127.0.0.1:{server.server_port}/api/v2/vn/apps",
        )
        provider = AppleRssStoreProvider(timeout_seconds=1)

        with pytest.raises(ValueError, match="SOURCE_FAILURE"):
            provider.get_chart_snapshot(
                store="app_store", country="VN", chart_type="top_free", limit=10
            )

        assert requests == ["/api/v2/vn/apps/top-free/50/apps.json"]
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "payload",
    [
        {"feed": {"country": "vn", "updated": "2026-10-15T00:00:00Z", "results": "bad"}},
        {"feed": {"country": "us", "updated": "2026-10-15T00:00:00Z", "results": []}},
        {"feed": {"country": "vn", "updated": "", "results": []}},
    ],
)
def test_invalid_feed_payload_is_an_explicit_source_failure(payload):
    provider = AppleRssStoreProvider(fetch_json=lambda _url: payload)

    with pytest.raises(ValueError, match="SOURCE_FAILURE.*invalid Apple RSS payload"):
        provider.get_chart_snapshot(
            store="app_store", country="VN", chart_type="top_free", limit=10
        )


def test_provider_selection_defaults_to_fixture_and_apple_is_explicit(tmp_path, monkeypatch):
    from gamota_research.mcp_server import _build_store_provider

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        '{"generated_for_testing":true,"source_mode":"FIXTURE",'
        '"provider":"synthetic","store_games":[],"chart_snapshots":[]}',
        encoding="utf-8",
    )
    monkeypatch.delenv("GAMOTA_STORE_PROVIDER", raising=False)

    fixture_provider = _build_store_provider(fixture_path)
    assert fixture_provider.provider_name == "synthetic"
    assert fixture_provider.source_mode == "FIXTURE"

    monkeypatch.setenv("GAMOTA_STORE_PROVIDER", "apple_rss")
    apple_provider = _build_store_provider(fixture_path)
    assert apple_provider.provider_name == "apple_rss"
    assert apple_provider.source_mode == "LIVE"

    monkeypatch.setenv("GAMOTA_STORE_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported GAMOTA_STORE_PROVIDER"):
        _build_store_provider(fixture_path)


def test_apple_rss_snapshot_survives_database_reopen(tmp_path):
    from gamota_research.db import Database
    from gamota_research.domain.store_service import StoreService
    from gamota_research.repository import ResearchRepository

    payload = _feed(_app("51", "Persisted App"))
    database_path = tmp_path / "apple-rss.sqlite3"
    database = Database(database_path)
    repository = ResearchRepository(database)
    run = repository.create_run("Persist one Apple RSS snapshot")
    service = StoreService(
        repository,
        AppleRssStoreProvider(fetch_json=lambda _url: payload),
    )

    snapshot = service.get_chart_snapshot(
        run_id=run.id,
        store="app_store",
        country="VN",
        chart_type="top_free",
        limit=10,
    )
    database.close()

    reopened = Database(database_path)
    try:
        reopened_service = StoreService(ResearchRepository(reopened), service.provider)
        history = reopened_service.get_chart_history(
            run_id=run.id,
            store="app_store",
            country="VN",
            chart_type="top_free",
            game_id="apple_rss:51",
        )
    finally:
        reopened.close()

    assert snapshot.source_mode == "LIVE"
    assert history["observation_count"] == 1
    assert history["insufficient_history"] is True
    assert history["observations"][0]["observed_at"] == "2026-10-15T00:00:00+00:00"
    assert history["observations"][0]["source_mode"] == "LIVE"
    assert history["observations"][0]["source_url"].endswith(
        "/top-free/50/apps.json"
    )


def test_apple_source_failure_is_an_explicit_mcp_tool_error(tmp_path):
    from gamota_research.db import Database
    from gamota_research.domain.store_service import StoreService
    from gamota_research.mcp_server import create_mcp_server
    from gamota_research.repository import ResearchRepository
    from gamota_research.service import ResearchService

    calls: list[str] = []

    def unavailable(url: str):
        calls.append(url)
        raise TimeoutError("simulated Apple RSS outage")

    database = Database(tmp_path / "apple-rss-error.sqlite3")
    repository = ResearchRepository(database)
    run = repository.create_run("Observe an Apple RSS failure")
    research_service = ResearchService(repository)
    research_service.set_research_contract(
        run.id,
        {
            "question": "Can an unavailable Apple RSS source fail explicitly?",
            "decision_goal": "Verify explicit source failure behavior",
            "geography": ["VN"],
            "metrics": ["store_rank"],
            "domain_tool_budget": 1,
        },
    )
    server = create_mcp_server(
        research_service,
        StoreService(repository, AppleRssStoreProvider(fetch_json=unavailable)),
    )

    async def invoke():
        async with _protocol_session(server) as session:
            result = await session.call_tool(
                "get_store_chart_snapshot",
                {
                    "run_id": run.id,
                    "store": "app_store",
                    "country": "VN",
                    "chart_type": "top_free",
                    "limit": 5,
                },
            )
            assert result.is_error is True
            assert "SOURCE_FAILURE" in str(result.content)

    try:
        anyio.run(invoke)
    finally:
        database.close()

    assert len(calls) == 1
