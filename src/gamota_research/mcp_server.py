from __future__ import annotations

import os
import secrets
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from .db import Database
from .domain.apple_rss_provider import AppleRssStoreProvider
from .domain.fixture_provider import FixtureStoreProvider
from .domain.store_service import StoreService
from .mcp_tools import register_research_tools
from .repository import ResearchRepository
from .service import ResearchService
from .validator import Validator


class StaticBearerTokenVerifier(TokenVerifier):
    """Verify a pre-shared bearer token without logging or exposing its value."""

    def __init__(self, token: str, resource_url: str) -> None:
        self._token = token
        self._resource_url = resource_url

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id="gamota-mission2",
            scopes=["gamota:research"],
            resource=self._resource_url,
        )


def _http_auth_settings(token: str | None, resource_url: str | None):
    if not token and not resource_url:
        return None, None
    if not token or not resource_url:
        raise ValueError(
            "GAMOTA_MCP_BEARER_TOKEN and GAMOTA_PUBLIC_MCP_URL must both be configured"
        )
    verifier = StaticBearerTokenVerifier(token, resource_url)
    settings = AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl(resource_url),
        required_scopes=["gamota:research"],
        validate_token_resource=True,
    )
    return verifier, settings


def create_mcp_server(
    service: ResearchService,
    store_service: StoreService | None = None,
    *,
    http_bearer_token: str | None = None,
    public_mcp_url: str | None = None,
) -> MCPServer:
    verifier, auth = _http_auth_settings(http_bearer_token, public_mcp_url)
    server = MCPServer(
        name="gamota-research",
        version="0.1.0",
        token_verifier=verifier,
        auth=auth,
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
    transport = os.environ.get("GAMOTA_TRANSPORT", "stdio").strip().casefold()
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("GAMOTA_TRANSPORT must be 'stdio' or 'streamable-http'")
    database = Database(_database_path())
    repository = ResearchRepository(database)
    service = ResearchService(repository)
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "store_fixture.json"
    )
    store_service = StoreService(repository, _build_store_provider(fixture_path))
    server = create_mcp_server(
        service,
        store_service,
        http_bearer_token=os.environ.get("GAMOTA_MCP_BEARER_TOKEN")
        if transport == "streamable-http"
        else None,
        public_mcp_url=os.environ.get("GAMOTA_PUBLIC_MCP_URL")
        if transport == "streamable-http"
        else None,
    )
    try:
        if transport == "streamable-http":
            if not os.environ.get("GAMOTA_MCP_BEARER_TOKEN"):
                raise ValueError("GAMOTA_MCP_BEARER_TOKEN is required for HTTP transport")
            if not os.environ.get("GAMOTA_PUBLIC_MCP_URL"):
                raise ValueError("GAMOTA_PUBLIC_MCP_URL is required for HTTP transport")
            server.run(
                transport="streamable-http",
                host=os.environ.get("GAMOTA_HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")),
            )
        else:
            server.run(transport="stdio")
    finally:
        database.close()


if __name__ == "__main__":
    main()
