from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from .db import Database
from .domain.apple_rss_provider import AppleRssStoreProvider
from .domain.fixture_provider import FixtureStoreProvider
from .domain.store_service import StoreService
from .mcp_tools import register_research_tools
from .oauth_auth import CompositeTokenVerifier, ToolScopeMiddleware
from .oauth_provider import OAuthAccessTokenVerifier, OAuthStore
from .repository import ResearchRepository
from .reports import ReportService
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


def _http_auth_settings(
    token: str | None,
    resource_url: str | None,
    *,
    oauth_verifier: OAuthAccessTokenVerifier | None = None,
    issuer_url: str | None = None,
):
    if not token and not resource_url:
        return None, None
    if not token or not resource_url:
        raise ValueError(
            "GAMOTA_MCP_BEARER_TOKEN and GAMOTA_PUBLIC_MCP_URL must both be configured"
        )
    parsed_resource = urlsplit(resource_url)
    issuer = issuer_url or f"{parsed_resource.scheme}://{parsed_resource.netloc}"
    verifier = (
        CompositeTokenVerifier(token, oauth_verifier, resource_url)
        if oauth_verifier is not None
        else StaticBearerTokenVerifier(token, resource_url)
    )
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=AnyHttpUrl(resource_url),
        required_scopes=None,
        validate_token_resource=True,
    )
    return verifier, settings


def create_mcp_server(
    service: ResearchService,
    store_service: StoreService | None = None,
    *,
    http_bearer_token: str | None = None,
    public_mcp_url: str | None = None,
    public_site_url: str | None = None,
    report_service: ReportService | None = None,
    oauth_verifier: OAuthAccessTokenVerifier | None = None,
    oauth_issuer_url: str | None = None,
) -> MCPServer:
    verifier, auth = _http_auth_settings(
        http_bearer_token,
        public_mcp_url,
        oauth_verifier=oauth_verifier,
        issuer_url=oauth_issuer_url,
    )
    server = MCPServer(
        name="gamota-research",
        version="0.1.0",
        token_verifier=verifier,
        auth=auth,
        middleware=(
            [
                ToolScopeMiddleware(
                    f"{urlsplit(public_mcp_url).scheme}://{urlsplit(public_mcp_url).netloc}"
                    "/.well-known/oauth-protected-resource"
                    f"{urlsplit(public_mcp_url).path}"
                )
            ]
            if verifier is not None and public_mcp_url
            else None
        ),
        instructions=(
            "Treat the user's ordinary, plain-language game-market research request as "
            "enough to begin; do not require them to name MCP tools, provide a run_id or "
            "report_id, or write a URL placeholder. Infer the game, market, platform, metric, "
            "and period from their request and conversation; ask only for a missing detail "
            "that would materially change the answer. Use the host's native web search and "
            "fetch tools for public-source discovery; this MCP stores and validates research "
            "evidence rather than providing generic web search. Create a run and contract, "
            "save sources and quoted evidence before claims, link claims to evidence, and "
            "record gaps or conflicts. Prefer direct publisher, official store, original "
            "research, or primary documents when available; trace secondary reporting to its "
            "underlying origin and record when provenance is derived or unknown. Treat source "
            "type and provenance as recorded metadata, not an automatic quality score. For "
            "time-sensitive questions, set an explicit freshness_cutoff and record publication "
            "date separately from the metric observation date; missing dates mean freshness is "
            "unknown, not current. Compare conflicts only after aligning metric, unit, market, "
            "platform, period, population, and method. Keep validator-supported claims distinct "
            "from agent interpretation, estimates, and unresolved assumptions. Use source and "
            "issue follow-up guidance to continue searching with native host tools, save new "
            "evidence in a new run, rerun validation, and leave unsupported questions open. "
            "Do not present host-supplied URLs or quotations as independently verified. Use "
            "claim_type ESTIMATE for third-party estimates and "
            "RECOMMENDATION for evidence-linked actions. Finalize the run, then publish a "
            "Game Decision Brief when the evidence supports a useful report. After publishing, "
            "use the returned report_id internally to call get_published_report and confirm "
            "the exact findings and limits. For a request to revisit an existing report, find "
            "it through list_published_reports and use its ID internally. In the same chat, "
            "answer naturally in the user's language with the verdict, 2–3 key findings, "
            "confidence, and important unknowns. Include a friendly Markdown link such as "
            "'Mở báo cáo đầy đủ' using the exact public_url returned by the MCP. Keep run IDs, "
            "report IDs, tool names, and URL field names out of the user-facing answer unless "
            "the user asks for them. Never invent a URL; if the MCP did not return a public "
            "link, briefly say that the report is saved but a web link was not returned. Do "
            "not claim publication succeeded unless publish and read-back succeed. "
            "Partial or "
            "insufficient-data findings are valid; never fill missing evidence with guesses. "
            "Read published reports with list_published_reports/get_published_report. "
            "Persist sources and evidence before saving claims. The store provider defaults "
            "to FIXTURE; set GAMOTA_STORE_PROVIDER=apple_rss explicitly for LIVE Apple RSS. "
            "Apple RSS exposes Vietnam Top Free/Top Paid Apps, not a games-only or "
            "Top Grossing chart. Missing genres remain unknown. Store rank is a visibility "
            "proxy and does not establish revenue, downloads, or DAU. This server does "
            "not call an LLM."
        ),
    )
    register_research_tools(
        server,
        service,
        Validator(service.repository),
        store_service,
        report_service or ReportService(
            service.repository,
            os.environ.get(
                "GAMOTA_REPORTS_DIR",
                str(Path.cwd() / "web" / "public" / "reports"),
            ),
        ),
        public_site_url=public_site_url
        or (
            f"{urlsplit(public_mcp_url).scheme}://{urlsplit(public_mcp_url).netloc}"
            if public_mcp_url
            else None
        ),
    )
    return server


def _database_path() -> Path:
    configured_path = os.environ.get("GAMOTA_RESEARCH_DB")
    if configured_path:
        return Path(configured_path).expanduser()
    return Path.home() / ".local" / "share" / "gamota-research-mcp" / "research.sqlite3"


def _http_transport_security_settings() -> TransportSecuritySettings:
    configured_origins = [
        origin.strip()
        for origin in os.environ.get("GAMOTA_MCP_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            *configured_origins,
        ],
    )


def _http_auth_mode() -> str:
    """Return the configured HTTP auth mode, requiring an explicit public-write opt-in."""
    mode = os.environ.get("GAMOTA_MCP_HTTP_AUTH", "bearer").strip().casefold()
    if mode not in {"bearer", "none"}:
        raise ValueError("GAMOTA_MCP_HTTP_AUTH must be 'bearer' or 'none'")
    if mode == "none" and os.environ.get("GAMOTA_MCP_PUBLIC_WRITES") != "true":
        raise ValueError(
            "GAMOTA_MCP_PUBLIC_WRITES=true is required to expose write tools without authentication"
        )
    return mode


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
    auth_mode = _http_auth_mode() if transport == "streamable-http" else "bearer"
    database = Database(_database_path())
    repository = ResearchRepository(database)
    service = ResearchService(repository)
    reports_dir = Path(
        os.environ.get(
            "GAMOTA_REPORTS_DIR",
            str(Path.cwd() / "web" / "public" / "reports"),
        )
    ).expanduser()
    report_service = ReportService(repository, reports_dir)
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "store_fixture.json"
    )
    store_service = StoreService(repository, _build_store_provider(fixture_path))
    oauth_db = os.environ.get("GAMOTA_OAUTH_DB") if transport == "streamable-http" else None
    oauth_issuer_url = os.environ.get("GAMOTA_OAUTH_ISSUER_URL")
    oauth_verifier = None
    if oauth_db:
        if not os.environ.get("GAMOTA_PUBLIC_MCP_URL"):
            raise ValueError("GAMOTA_PUBLIC_MCP_URL is required when OAuth is enabled")
        resource_url = os.environ["GAMOTA_PUBLIC_MCP_URL"]
        parsed_resource = urlsplit(resource_url)
        oauth_issuer_url = oauth_issuer_url or f"{parsed_resource.scheme}://{parsed_resource.netloc}"
        oauth_verifier = OAuthAccessTokenVerifier(
            OAuthStore(Path(oauth_db).expanduser()),
            issuer=oauth_issuer_url,
            resource=resource_url,
        )
    server = create_mcp_server(
        service,
        store_service,
        http_bearer_token=os.environ.get("GAMOTA_MCP_BEARER_TOKEN")
        if transport == "streamable-http" and auth_mode == "bearer"
        else None,
        public_mcp_url=os.environ.get("GAMOTA_PUBLIC_MCP_URL")
        if transport == "streamable-http" and auth_mode == "bearer"
        else None,
        report_service=report_service,
        oauth_verifier=oauth_verifier,
        oauth_issuer_url=oauth_issuer_url,
        public_site_url=os.environ.get("GAMOTA_PUBLIC_SITE_URL"),
    )
    try:
        if transport == "streamable-http":
            if auth_mode == "bearer" and not os.environ.get("GAMOTA_MCP_BEARER_TOKEN"):
                raise ValueError("GAMOTA_MCP_BEARER_TOKEN is required for HTTP transport")
            if auth_mode == "bearer" and not os.environ.get("GAMOTA_PUBLIC_MCP_URL"):
                raise ValueError("GAMOTA_PUBLIC_MCP_URL is required for HTTP transport")
            server.run(
                transport="streamable-http",
                host=os.environ.get("GAMOTA_HOST", "127.0.0.1"),
                port=int(os.environ.get("GAMOTA_MCP_PORT", os.environ.get("PORT", "8000"))),
                transport_security=_http_transport_security_settings(),
            )
        else:
            server.run(transport="stdio")
    finally:
        database.close()


if __name__ == "__main__":
    main()
