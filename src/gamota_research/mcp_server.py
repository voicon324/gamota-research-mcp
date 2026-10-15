from __future__ import annotations

import os
from pathlib import Path

from mcp.server import MCPServer

from .db import Database
from .domain.apple_rss_provider import AppleRssStoreProvider
from .domain.fixture_provider import FixtureStoreProvider
from .domain.store_service import StoreService
from .mcp_tools import register_research_tools
from .repository import ResearchRepository
from .service import ResearchService
from .validator import Validator


def create_mcp_server(
    service: ResearchService, store_service: StoreService | None = None
) -> MCPServer:
    server = MCPServer(
        name="gamota-research",
        version="0.1.0",
        instructions=(
            "Use the host's native web search for public-source discovery; this MCP "
            "stores and validates research evidence rather than providing generic web search. "
            "Persist sources and evidence before saving claims. The store provider defaults "
            "to FIXTURE; set GAMOTA_STORE_PROVIDER=apple_rss explicitly for LIVE Apple RSS. "
            "Apple RSS exposes Vietnam Top Free/Top Paid Apps, not a games-only or "
            "Top Grossing chart. Missing genres remain unknown. Store rank is a visibility "
            "proxy and does not establish revenue, downloads, or DAU. This server does "
            "not call an LLM."
        ),
    )
    register_research_tools(
        server, service, Validator(service.repository), store_service
    )
    return server


def _database_path() -> Path:
    configured_path = os.environ.get("GAMOTA_RESEARCH_DB")
    if configured_path:
        return Path(configured_path).expanduser()
    return Path.home() / ".local" / "share" / "gamota-research-mcp" / "research.sqlite3"


def _build_store_provider(fixture_path: Path):
    provider_name = os.environ.get("GAMOTA_STORE_PROVIDER", "fixture").strip().casefold()
    if provider_name == "fixture":
        return FixtureStoreProvider(fixture_path)
    if provider_name == "apple_rss":
        return AppleRssStoreProvider()
    raise ValueError(
        f"Unsupported GAMOTA_STORE_PROVIDER={provider_name!r}; use 'fixture' or 'apple_rss'"
    )


def main() -> None:
    database = Database(_database_path())
    repository = ResearchRepository(database)
    service = ResearchService(repository)
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "store_fixture.json"
    )
    store_service = StoreService(repository, _build_store_provider(fixture_path))
    server = create_mcp_server(service, store_service)
    try:
        server.run()
    finally:
        database.close()


if __name__ == "__main__":
    main()
